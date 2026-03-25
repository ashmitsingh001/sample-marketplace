import os
import zipfile
import tempfile
import time
import logging
import argparse
from config import *
from metadata import extract_metadata, sanitize_filename
from audio import generate_preview, generate_waveform
from storage import SupabaseStorageProvider, TelegramStorageProvider
from db import DatabaseManager

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def process_pack(zip_path, db_manager, storage_provider, tg_provider):
    start_time = time.time()
    pack_name = os.path.basename(zip_path).rsplit('.', 1)[0]
    
    # 1. Register Pack
    logging.info(f"Registering pack: {pack_name}")
    pack = db_manager.get_pack_by_id(pack_name)
    if not pack:
        pack = db_manager.upsert_pack({
            'external_id': pack_name,
            'title': pack_name.replace('_', ' ').title(),
            'processing_status': 'processing'
        })
    
    if not pack:
        logging.error("Failed to register pack in DB.")
        return

    pack_id = pack['id']
    pack_slug = pack.get('slug', pack_name.lower())

    # 2. Telegram Upload (ZIP)
    if not pack.get('pack_file_id'):
        if DRY_RUN:
            logging.info("[DRY-RUN] Skipping Telegram ZIP upload.")
            file_id = "dry-run-id"
        else:
            logging.info("Uploading ZIP to Telegram...")
            file_id = tg_provider.upload_zip(zip_path)
        
        if not file_id:
            db_manager.update_pack_status(pack_id, 'failed')
            logging.error("Telegram upload failed. Stopping.")
            return
        db_manager.upsert_pack({'id': pack_id, 'pack_file_id': file_id})
    
    # 3. Processing Loop
    with tempfile.TemporaryDirectory() as tmpdir:
        logging.info(f"Unzipping {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)
        
        # Build File List
        audio_files = []
        for root, _, files in os.walk(tmpdir):
            for f in files:
                if any(f.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    audio_files.append(os.path.join(root, f))
        
        logging.info(f"Found {len(audio_files)} samples.")
        
        processed_count = 0
        failed_count = 0
        skipped_count = 0

        for audio_path in audio_files:
            # Timeout Check
            elapsed = (time.time() - start_time) / 60
            if elapsed > MAX_RUNTIME_MINUTES:
                logging.warning("Approaching timeout limit. Stopping loop.")
                db_manager.update_pack_status(pack_id, 'partial')
                break
            
            if processed_count >= MAX_FILES_PER_RUN:
                logging.info(f"Reached batch limit ({MAX_FILES_PER_RUN}).")
                db_manager.update_pack_status(pack_id, 'partial')
                break

            orig_filename = os.path.basename(audio_path)
            
            # Idempotency Check
            status = db_manager.get_sample_status(pack_id, orig_filename)
            if status and status.get('processing_status') == 'completed' and status.get('preview_url'):
                skipped_count += 1
                continue
            
            # Process Sample
            logging.info(f"Processing: {orig_filename}")
            try:
                # Meta
                meta = extract_metadata(orig_filename)
                sanitized = sanitize_filename(orig_filename)
                
                # Previews
                preview_file = os.path.join(tmpdir, f"{sanitized}.mp3")
                waveform_file = os.path.join(tmpdir, f"{sanitized}.json")
                
                if generate_preview(audio_path, preview_file) and generate_waveform(audio_path, waveform_file):
                    # Upload
                    s_path = f"{pack_slug}/{sanitized}"
                    if DRY_RUN:
                        logging.info(f"[DRY-RUN] Skipping storage upload for {sanitized}")
                        p_url = f"https://dry-run.com/{sanitized}.mp3"
                        w_url = f"https://dry-run.com/{sanitized}.json"
                    else:
                        p_url = storage_provider.upload_file(preview_file, f"{s_path}.mp3")
                        w_url = storage_provider.upload_file(waveform_file, f"{s_path}.json")
                    
                    if p_url and w_url:
                        # DB Sync
                        sample_data = {
                            'pack_id': pack_id,
                            'filename': orig_filename,
                            'title': orig_filename.rsplit('.', 1)[0],
                            'bpm': meta['bpm'],
                            'musical_key': meta['key'],
                            'preview_url': p_url,
                            'metadata': {'waveform_url': w_url},
                            'processing_status': 'completed'
                        }
                        if DRY_RUN:
                            logging.info(f"[DRY-RUN] Skipping DB upsert for {orig_filename}")
                        else:
                            db_manager.upsert_sample(sample_data)
                        processed_count += 1
                    else:
                        raise Exception("Upload failed")
                else:
                    raise Exception("FFmpeg/Audiowaveform failed")
                    
            except Exception as e:
                logging.error(f"Failed processing {orig_filename}: {e}")
                db_manager.upsert_sample({
                    'pack_id': pack_id,
                    'filename': orig_filename,
                    'processing_status': 'failed'
                })
                failed_count += 1
        
        # Final Report
        logging.info(f"Done! Processed: {processed_count}, Skipped: {skipped_count}, Failed: {failed_count}")
        if failed_count == 0 and processed_count + skipped_count >= len(audio_files):
            db_manager.update_pack_status(pack_id, 'completed')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, help="Path to sample pack ZIP")
    args = parser.parse_args()
    
    # Init Managers (Mocked with env vars)
    db = DatabaseManager(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    storage = SupabaseStorageProvider(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    tg = TelegramStorageProvider(os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID'])
    
    process_pack(args.zip, db, storage, tg)
