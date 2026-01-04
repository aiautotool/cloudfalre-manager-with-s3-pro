import requests

class CloudflareAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_zones(self):
        url = f"{self.base_url}/zones"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                return data["result"]
        return []

    def get_zone_id(self, domain):
        url = f"{self.base_url}/zones"
        params = {"name": domain}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data["success"] and data["result"]:
                return data["result"][0]["id"]
        return None

    def list_dns_records(self, zone_id, record_type=None):
        url = f"{self.base_url}/zones/{zone_id}/dns_records"
        params = {}
        if record_type:
            params["type"] = record_type
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                return data["result"]
        return []

    def create_dns_record(self, zone_id, type, name, content, ttl=120, proxied=False):
        url = f"{self.base_url}/zones/{zone_id}/dns_records"
        payload = {
            "type": type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied
        }
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()

    def update_dns_record(self, zone_id, record_id, type, name, content, ttl=120, proxied=False):
        url = f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}"
        payload = {
            "type": type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied
        }
        response = requests.put(url, headers=self.headers, json=payload)
        return response.json()

    def delete_dns_record(self, zone_id, record_id):
        url = f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}"
        response = requests.delete(url, headers=self.headers)
        return response.json()

    def get_accounts(self):
        url = f"{self.base_url}/accounts"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                return data["result"]
        return []

    def create_zone(self, name, account_id, type="full"):
        url = f"{self.base_url}/zones"
        payload = {
            "name": name,
            "account": {"id": account_id},
            "type": type
        }
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()

    def delete_zone(self, zone_id):
        url = f"{self.base_url}/zones/{zone_id}"
        response = requests.delete(url, headers=self.headers)
        return response.json()
