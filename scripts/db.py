import requests
import logging
from config import DRY_RUN_DB

class DatabaseManager:
    def __init__(self, url, key):
        self.url = f"{url}/rest/v1"
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation,resolution=merge-duplicates"
        }

    def get_pack_by_id(self, external_id):
        if DRY_RUN_DB:
            logging.info(f"[DRY-RUN-DB] Mock get_pack_by_id: {external_id}")
            return {'id': 'mock-pack-id', 'slug': external_id.lower()}
        logging.info(f"DB: Fetching pack {external_id} from Supabase")
        resp = requests.get(f"{self.url}/packs?external_id=eq.{external_id}", headers=self.headers)
        data = resp.json()
        return data[0] if data else None

    def upsert_pack(self, pack_data):
        if DRY_RUN_DB:
            logging.info(f"[DRY-RUN-DB] Mock upsert_pack: {pack_data.get('external_id')}")
            return {'id': 'mock-pack-id', 'slug': pack_data.get('external_id', 'mock').lower()}
        logging.info(f"DB: Writing pack {pack_data.get('external_id')} to Supabase")
        resp = requests.post(f"{self.url}/packs", json=pack_data, headers=self.headers)
        data = resp.json()
        return data[0] if data else None

    def get_sample_status(self, pack_id, filename):
        if DRY_RUN_DB:
            return None # Force processing in dry run
        resp = requests.get(
            f"{self.url}/samples?pack_id=eq.{pack_id}&filename=eq.{filename}",
            headers=self.headers
        )
        data = resp.json()
        return data[0] if data else None

    def upsert_sample(self, sample_data):
        if DRY_RUN_DB:
            logging.info(f"[DRY-RUN-DB] Mock upsert_sample: {sample_data.get('filename')}")
            return True
        logging.info(f"DB: Writing sample metadata for {sample_data.get('filename')}")
        # Using PostgREST upsert logic (Prefer: resolution=merge-duplicates)
        resp = requests.post(f"{self.url}/samples", json=sample_data, headers=self.headers)
        return resp.status_code in [200, 201]

    def update_pack_status(self, pack_id, status):
        if DRY_RUN_DB:
            logging.info(f"[DRY-RUN-DB] Mock update_pack_status: {status}")
            return True
        logging.info(f"DB: Updating pack status to {status}")
        resp = requests.patch(
            f"{self.url}/packs?id=eq.{pack_id}",
            json={'processing_status': status},
            headers=self.headers
        )
        return resp.status_code == 204
