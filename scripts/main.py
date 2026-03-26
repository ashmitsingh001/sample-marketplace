import os
import zipfile
import tempfile
import time
import logging
import argparse
import shutil
from config import *
from metadata import extract_metadata, sanitize_filename
from audio import generate_preview, generate_waveform
from storage import SupabaseStorageProvider, TelegramStorageProvider, R2StorageProvider
from db import DatabaseManager
from zip_indexer import ZipIndexer

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def process_pack(zip_remote_path, db_manager, storage_previews, storage_supabase_packs, storage_r2, tg_provider):
    """
    Refined flow for Module 2.5: ZIP Indexing & On-Demand Extraction.
    """
    start_time = time.time()
    pack_name = os.path.basename(zip_remote_path).rsplit('.', 1)[0]
    
    # 1. Register Pack
    logging.info(f"Registering/Fetching pack: {pack_name}")
    pack = db_manager.get_pack_by_id(pack_name)
    if not pack:
        pack = db_manager.upsert_pack({
            'external_id': pack_name,
            'title': pack_name.replace('_', ' ').title(),
            'slug': pack_name.lower(),
            'processing_status': 'processing'
        })
    
    if not pack:
        logging.error("Failed to register pack in DB.")
        return

    pack_id = pack['id']
    pack_slug = pack.get('slug', pack_name.lower())

    # 2. Setup Local Working Space
    with tempfile.TemporaryDirectory() as tmpdir:
        local_zip = os.path.join(tmpdir, "source.zip")
        final_zip = os.path.join(tmpdir, "final.zip")
        
        # Step A: Download ZIP from Supabase
        if not storage_packs.download_file(zip_remote_path, local_zip):
            logging.error("Failed to download ZIP from Supabase Storage.")
            return

        # Step B: Initial Scan
        logging.info("Step B: Performing initial ZIP scan...")
        initial_index = ZipIndexer.get_index(local_zip)
        needs_repack = any(e['needs_repack'] for e in initial_index)
        
        # Step C: Conditional Repack (Normalize to STORE mode)
        if needs_repack:
            logging.info("Repack requested: Normalizing ZIP to STORE mode (no compression)...")
            with zipfile.ZipFile(local_zip, 'r') as zin:
                with zipfile.ZipFile(final_zip, 'w', compression=zipfile.ZIP_STORED) as zout:
                    for item in zin.infolist():
                        if item.is_dir(): continue
                        zout.writestr(item.filename, zin.read(item.filename))
        else:
            logging.info("ZIP is already optimized (STORE mode). Skipping repack.")
            shutil.copy2(local_zip, final_zip)

        # Step D: Final Indexing (Single Source of Truth)
        logging.info("Step D: Performing final Data-Level Indexing...")
        final_index = ZipIndexer.get_index(final_zip)
        
        # Step E: Upload Optimized ZIP back to to the correct provider
        zip_size = os.path.getsize(final_zip)
        storage_provider = 'r2' if zip_size > 40 * 1024 * 1024 else 'supabase'
        
        logging.info(f"Final ZIP size: {zip_size / (1024*1024):.2f}MB. Selecting provider: {storage_provider}")
        
        if storage_provider == 'r2':
            storage_packs = storage_r2
        else:
            storage_packs = storage_supabase_packs
            
        logging.info(f"Uploading optimized ZIP ({storage_provider})...")
        storage_packs.upload_file(final_zip, zip_remote_path)
        
        # Update Pack with indexed ZIP path, size and provider
        db_manager.update_pack(pack_id, {
            'zip_path': zip_remote_path,
            'is_indexed': True,
            'storage_provider': storage_provider,
            'zip_size': zip_size
        })

        # 3. Processing Loop (Using Final Index)
        audio_files = [e for e in final_index if e['is_audio']]
        logging.info(f"Found {len(audio_files)} audio samples to index.")
        
        processed_count = 0
        failed_count = 0
        skipped_count = 0

        # Open the final ZIP once for efficient extraction during loop
        with zipfile.ZipFile(final_zip, 'r') as z:
            for entry in audio_files:
                orig_filename = entry['filename']
                
                # Timeout/Batch Checks
                elapsed = (time.time() - start_time) / 60
                if elapsed > MAX_RUNTIME_MINUTES or processed_count >= MAX_FILES_PER_RUN:
                    db_manager.update_pack_status(pack_id, 'partial')
                    break

                # Idempotency Check
                status = db_manager.get_sample_status(pack_id, orig_filename)
                if status and status.get('processing_status') == 'completed' and status.get('is_indexed'):
                    skipped_count += 1
                    continue
                
                logging.info(f"Processing: {orig_filename}")
                try:
                    # Extract to temp for preview generation
                    sanitized = sanitize_filename(os.path.basename(orig_filename))
                    local_sample_path = os.path.join(tmpdir, f"extract_{sanitized}.wav")
                    
                    with open(local_sample_path, 'wb') as f:
                        f.write(z.read(orig_filename))

                    # 4. Generate Previews (MP3 + Waveform)
                    meta = extract_metadata(orig_filename)
                    preview_file = os.path.join(tmpdir, f"{sanitized}.mp3")
                    waveform_file = os.path.join(tmpdir, f"{sanitized}.json")
                    
                    if generate_preview(local_sample_path, preview_file) and generate_waveform(local_sample_path, waveform_file):
                        # Upload to Previews Bucket
                        s_path = f"{pack_slug}/{sanitized}"
                        p_url = storage_previews.upload_file(preview_file, f"{s_path}.mp3")
                        w_url = storage_previews.upload_file(waveform_file, f"{s_path}.json")

                        if p_url and w_url:
                            # 5. Save to DB with Byte Offsets
                            sample_data = {
                                'pack_id': pack_id,
                                'filename': orig_filename,
                                'title': os.path.basename(orig_filename).rsplit('.', 1)[0],
                                'bpm': meta['bpm'],
                                'musical_key': meta['key'],
                                'category': meta['category'],
                                'preview_url': p_url,
                                'extra_metadata': {'waveform_url': w_url},
                                'processing_status': 'completed',
                                # --- Advanced Indexing Fields ---
                                'data_start': entry['data_start'],
                                'data_end': entry['data_end'],
                                'file_size': entry['file_size'],
                                'compression_method': entry['compression_method'],
                                'zip_path': zip_remote_path,
                                'storage_provider': storage_provider,
                                'is_indexed': True
                            }
                            db_manager.upsert_sample(sample_data)
                            processed_count += 1
                        else:
                            raise Exception("Preview upload failed")
                    else:
                        raise Exception("FFmpeg failed")
                        
                except Exception as e:
                    logging.error(f"Failed {orig_filename}: {e}")
                    db_manager.upsert_sample({'pack_id': pack_id, 'filename': orig_filename, 'processing_status': 'failed'})
                    failed_count += 1
        
        logging.info(f"Done! Processed: {processed_count}, Skipped: {skipped_count}, Failed: {failed_count}")
        if failed_count == 0 and processed_count + skipped_count >= len(audio_files):
            db_manager.update_pack_status(pack_id, 'completed')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-zip", required=True, help="Remote path in Supabase 'packs' bucket")
    args = parser.parse_args()
    
    # Init Managers
    s_url = os.environ.get('SUPABASE_URL')
    s_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    
    if not s_url or not s_key:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables.")
        exit(1)
        
    db = DatabaseManager(s_url, s_key)
    storage_previews = SupabaseStorageProvider(s_url, s_key, bucket='previews')
    storage_supabase_packs = SupabaseStorageProvider(s_url, s_key, bucket='packs')
    
    # Initialize R2 if credentials provided
    r2_acc = os.environ.get('R2_ACCOUNT_ID')
    r2_key = os.environ.get('R2_ACCESS_KEY')
    r2_sec = os.environ.get('R2_SECRET_KEY')
    r2_bucket = os.environ.get('R2_BUCKET_NAME', 'packs')
    
    storage_r2 = None
    if r2_acc and r2_key and r2_sec:
        storage_r2 = R2StorageProvider(r2_acc, r2_key, r2_sec, r2_bucket)
    else:
        logging.warning("R2 credentials not found. Defaulting all to Supabase.")
        storage_r2 = storage_supabase_packs

    tg = TelegramStorageProvider(os.environ.get('TELEGRAM_BOT_TOKEN', ''), os.environ.get('TELEGRAM_CHAT_ID', ''))
    
    process_pack(args.remote_zip, db, storage_previews, storage_supabase_packs, storage_r2, tg)
