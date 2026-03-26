import os
import requests
import logging
import hashlib
import hmac
import datetime
from config import DRY_RUN_STORAGE, TELEGRAM_SAMPLES_CHAT_ID

class StorageProvider:
    """Base class for storage abstraction"""
    def upload_file(self, local_path, remote_path): raise NotImplementedError
    def download_file(self, remote_path, local_path): raise NotImplementedError

class SupabaseStorageProvider(StorageProvider):
    def __init__(self, url, key, bucket='previews'):
        self.url = f"{url}/storage/v1/object/{bucket}"
        self.headers = {"Authorization": f"Bearer {key}", "x-upsert": "true"}

    def upload_file(self, local_path, remote_path):
        if DRY_RUN_STORAGE:
            logging.info(f"STORAGE: Skipped (DRY_RUN_STORAGE) for {remote_path}")
            return f"{remote_path}"
        with open(local_path, 'rb') as f:
            resp = requests.post(f"{self.url}/{remote_path}", headers=self.headers, data=f)
            if resp.status_code == 200:
                return f"{remote_path}"
            logging.error(f"Supabase upload failed: {resp.text}")
            return None

    def download_file(self, remote_path, local_path):
        """Downloads a file from Supabase storage for local processing."""
        logging.info(f"Downloading from Supabase: {remote_path}...")
        resp = requests.get(f"{self.url}/{remote_path}", headers=self.headers)
        if resp.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(resp.content)
            return True
        logging.error(f"Supabase download failed: {resp.text}")
        return False

class R2StorageProvider(StorageProvider):
    """
    Minimal Cloudflare R2 / S3 Storage Provider using manual SIGV4 signing.
    Avoids boto3 dependency.
    """
    def __init__(self, account_id, access_key, secret_key, bucket_name):
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket_name
        self.endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        self.region = "auto"
        self.service = "s3"

    def _sign(self, key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def _get_signature_key(self, key, date_stamp, region_name, service_name):
        k_date = self._sign(('AWS4' + key).encode('utf-8'), date_stamp)
        k_region = self._sign(k_date, region_name)
        k_service = self._sign(k_region, service_name)
        k_signing = self._sign(k_service, 'aws4_request')
        return k_signing

    def upload_file(self, local_path, remote_path):
        if DRY_RUN_STORAGE:
            logging.info(f"STORAGE (R2): Skipped (DRY_RUN_STORAGE) for {remote_path}")
            return f"{remote_path}"

        method = 'PUT'
        host = f"{self.bucket}.{os.path.basename(self.endpoint)}"
        endpoint_url = f"https://{host}/{remote_path}"
        
        t = datetime.datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')

        with open(local_path, 'rb') as f:
            payload = f.read()

        payload_hash = hashlib.sha256(payload).hexdigest()
        canonical_uri = '/' + remote_path
        canonical_querystring = ''
        canonical_headers = f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
        signed_headers = 'host;x-amz-content-sha256;x-amz-date'
        
        canonical_request = (f"{method}\n{canonical_uri}\n{canonical_querystring}\n"
                             f"{canonical_headers}\n{signed_headers}\n{payload_hash}")
        
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = (f"{algorithm}\n{amz_date}\n{credential_scope}\n"
                          f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}")

        signing_key = self._get_signature_key(self.secret_key, date_stamp, self.region, self.service)
        signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()

        headers = {
            'x-amz-date': amz_date,
            'x-amz-content-sha256': payload_hash,
            'Authorization': f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        }

        logging.info(f"Uploading to R2: {remote_path}...")
        resp = requests.put(endpoint_url, data=payload, headers=headers)
        
        if resp.status_code == 200:
            return f"{remote_path}"
        logging.error(f"R2 upload failed: {resp.status_code} {resp.text}")
        return None

    def download_file(self, remote_path, local_path):
        """
        Downloads a file from R2 storage.
        Note: Extraction usually happens in the Worker, but this is for ingestion-side downloads if needed.
        Requires GET signature logic (similar to PUT).
        """
        # For now, we return False as ingestion usually downloads from Supabase or local Source.
        logging.warning("R2 download_file not fully implemented (minimal version).")
        return False

class TelegramStorageProvider:
    def __init__(self, bot_token, chat_id):
        self.token = bot_token
        self.chat_id = chat_id  # PACKS channel
        self.samples_chat_id = TELEGRAM_SAMPLES_CHAT_ID  # SAMPLES channel
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def _send_document(self, chat_id, file_path, caption=None):
        """Core helper: sends a document to any channel and returns file_id."""
        try:
            # Check file size (Telegram Bot API limit is 50MB for most bots)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > 50:
                logging.warning(f"File {os.path.basename(file_path)} is {size_mb:.2f}MB, which exceeds Telegram's 50MB bot limit. Skipping.")
                return None

            with open(file_path, 'rb') as f:
                data = {'chat_id': chat_id}
                if caption:
                    data['caption'] = caption
                resp = requests.post(
                    f"{self.base_url}/sendDocument",
                    data=data,
                    files={'document': f}
                )
                result = resp.json()
                if result.get('ok'):
                    file_id = result['result']['document']['file_id']
                    logging.info(f"Upload successful → file_id: {file_id}")
                    return file_id
                
                # Special handling for size error just in case check fails
                if "file is too big" in str(result).lower():
                    logging.warning(f"Telegram rejected {os.path.basename(file_path)}: File too large.")
                    return None
                    
                logging.error(f"Telegram upload failed: {result}")
                return None
        except Exception as e:
            logging.error(f"Telegram API Error: {e}")
            return None

    def upload_zip(self, file_path, pack_id=None, pack_title=None):
        """Uploads ZIP to PACKS channel with structured caption. Returns file_id."""
        if DRY_RUN_STORAGE:
            logging.info("STORAGE: Skipped Telegram ZIP upload (DRY_RUN_STORAGE)")
            return "mock-telegram-file-id"
        caption = (
            f"📦 PACK\n"
            f"pack_id: {pack_id or 'unknown'}\n"
            f"title: {pack_title or 'unknown'}\n"
            f"type: zip"
        )
        logging.info("Uploading ZIP to Telegram (PACKS channel)...")
        return self._send_document(self.chat_id, file_path, caption=caption)

    def upload_sample(self, wav_path, metadata):
        """Uploads individual WAV to SAMPLES channel with structured caption. Returns file_id."""
        if DRY_RUN_STORAGE:
            logging.info(f"STORAGE: Skipped Telegram WAV upload (DRY_RUN_STORAGE) for {metadata.get('filename')}")
            return "mock-sample-file-id"
        if not self.samples_chat_id:
            logging.error("STORAGE: TELEGRAM_SAMPLES_CHAT_ID not configured. Skipping WAV upload.")
            return None
        caption = (
            f"🎧 SAMPLE\n"
            f"pack_id: {metadata.get('pack_id', 'unknown')}\n"
            f"filename: {metadata.get('filename', 'unknown')}\n"
            f"bpm: {metadata.get('bpm', 0)}\n"
            f"key: {metadata.get('key', 'Unknown')}\n"
            f"category: {metadata.get('category', 'Other')}"
        )
        logging.info(f"Uploading WAV to Telegram (SAMPLES channel): {metadata.get('filename')}")
        return self._send_document(self.samples_chat_id, wav_path, caption=caption)

