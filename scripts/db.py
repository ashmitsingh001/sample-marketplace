import requests
import logging

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
        resp = requests.get(f"{self.url}/packs?external_id=eq.{external_id}", headers=self.headers)
        data = resp.json()
        return data[0] if data else None

    def upsert_pack(self, pack_data):
        resp = requests.post(f"{self.url}/packs", json=pack_data, headers=self.headers)
        data = resp.json()
        return data[0] if data else None

    def get_sample_status(self, pack_id, filename):
        resp = requests.get(
            f"{self.url}/samples?pack_id=eq.{pack_id}&filename=eq.{filename}",
            headers=self.headers
        )
        data = resp.json()
        return data[0] if data else None

    def upsert_sample(self, sample_data):
        # Using PostgREST upsert logic (Prefer: resolution=merge-duplicates)
        resp = requests.post(f"{self.url}/samples", json=sample_data, headers=self.headers)
        return resp.status_code in [200, 201]

    def update_pack_status(self, pack_id, status):
        resp = requests.patch(
            f"{self.url}/packs?id=eq.{pack_id}",
            json={'processing_status': status},
            headers=self.headers
        )
        return resp.status_code == 204
