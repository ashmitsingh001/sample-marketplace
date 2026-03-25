import os
import requests
import logging

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
        with open(local_path, 'rb') as f:
            resp = requests.post(f"{self.url}/{remote_path}", headers=self.headers, data=f)
            if resp.status_code == 200:
                # Return the public URL (Note: Actual Supabase public URL logic might differ)
                # For this implementation, we assume a standard path format
                return f"{remote_path}"
            logging.error(f"Supabase upload failed: {resp.text}")
            return None

class TelegramStorageProvider:
    def __init__(self, bot_token, chat_id):
        self.token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def upload_zip(self, file_path):
        """Uploads ZIP to Telegram and returns file_id"""
        try:
            with open(file_path, 'rb') as f:
                resp = requests.post(
                    f"{self.base_url}/sendDocument",
                    data={'chat_id': self.chat_id},
                    files={'document': f}
                )
                data = resp.json()
                if data.get('ok'):
                    return data['result']['document']['file_id']
                logging.error(f"Telegram upload failed: {data}")
                return None
        except Exception as e:
            logging.error(f"Telegram API Error: {e}")
            return None
