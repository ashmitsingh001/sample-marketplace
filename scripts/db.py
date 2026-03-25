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
            "Prefer": "return=representation"
        }
        logging.info("DB: Manager Initialized (v1.0.2-header-fix)")

    def _safe_request(self, method, url, **kwargs):
        try:
            # Explicitly merge headers to avoid multiple values error
            custom_headers = kwargs.pop('headers', {})
            merged_headers = {**self.headers, **custom_headers}
            
            resp = requests.request(method, url, headers=merged_headers, **kwargs)
            logging.debug(f"DB Raw Response: {resp.status_code} - {resp.text}")
            
            if resp.status_code >= 400:
                logging.error(f"DB Error ({resp.status_code}): {resp.text}")
                return None
            
            if resp.status_code == 204:
                return True
                
            data = resp.json()
            if isinstance(data, list):
                if not data:
                    logging.debug("DB: Empty list returned")
                    return None
                return data[0]
            return data
        except Exception as e:
            logging.error(f"DB Request Exception: {e}")
            return None

    def get_pack_by_id(self, external_id):
        if DRY_RUN_DB:
            logging.info(f"[DRY-RUN-DB] Mock get_pack_by_id: {external_id}")
            return {'id': 'mock-pack-id', 'slug': external_id.lower()}
        logging.info(f"DB: Fetching pack {external_id}")
        return self._safe_request("GET", f"{self.url}/packs?external_id=eq.{external_id}")

    def upsert_pack(self, pack_data):
        if DRY_RUN_DB:
            logging.info(f"[DRY-RUN-DB] Mock upsert_pack: {pack_data.get('external_id')}")
            return {'id': 'mock-pack-id', 'slug': pack_data.get('external_id', 'mock').lower()}
        logging.info(f"DB: Upserting pack {pack_data.get('external_id')}")
        # Add resolution=merge-duplicates for upsert logic
        headers = self.headers.copy()
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        return self._safe_request("POST", f"{self.url}/packs", json=pack_data, headers=headers)

    def get_sample_status(self, pack_id, filename):
        if DRY_RUN_DB:
            return None
        return self._safe_request("GET", f"{self.url}/samples?pack_id=eq.{pack_id}&filename=eq.{filename}")

    def upsert_sample(self, sample_data):
        if DRY_RUN_DB:
            logging.info(f"[DRY-RUN-DB] Mock upsert_sample: {sample_data.get('filename')}")
            return True
        logging.info(f"DB: Upserting sample {sample_data.get('filename')}")
        headers = self.headers.copy()
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        result = self._safe_request("POST", f"{self.url}/samples", json=sample_data, headers=headers)
        return result is not None

    def update_pack_status(self, pack_id, status):
        if DRY_RUN_DB:
            logging.info(f"[DRY-RUN-DB] Mock update_pack_status: {status}")
            return True
        logging.info(f"DB: Updating pack {pack_id} status to {status}")
        return self._safe_request("PATCH", f"{self.url}/packs?id=eq.{pack_id}", json={'processing_status': status})
