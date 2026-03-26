import os
import requests
import logging
from config import DRY_RUN_STORAGE, TELEGRAM_SAMPLES_CHAT_ID

class StorageProvider:
    """Base class for storage abstraction"""
    def upload_preview(self, file_path, remote_path): raise NotImplementedError
    def upload_waveform(self, file_path, remote_path): raise NotImplementedError
    def upload_pack(self, file_path, remote_path): raise NotImplementedError

class SupabaseStorageProvider(StorageProvider):
    def __init__(self, url, key, bucket='previews'):
        self.url = f"{url}/storage/v1/object/{bucket}"
        self.headers = {"Authorization": f"Bearer {key}", "x-upsert": "true"}

    def upload_file(self, local_path, remote_path):
        if DRY_RUN_STORAGE:
            logging.info(f"STORAGE: Skipped (DRY_RUN_STORAGE) for {remote_path}")
            return f"https://dry-run.supabase.co/{remote_path}"
        with open(local_path, 'rb') as f:
            resp = requests.post(f"{self.url}/{remote_path}", headers=self.headers, data=f)
            if resp.status_code == 200:
                return f"{remote_path}"
            logging.error(f"Supabase upload failed: {resp.text}")
            return None

class TelegramStorageProvider:
    def __init__(self, bot_token, chat_id):
        self.token = bot_token
        self.chat_id = chat_id  # PACKS channel
        self.samples_chat_id = TELEGRAM_SAMPLES_CHAT_ID  # SAMPLES channel
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def _send_document(self, chat_id, file_path, caption=None):
        """Core helper: sends a document to any channel and returns file_id."""
        try:
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

