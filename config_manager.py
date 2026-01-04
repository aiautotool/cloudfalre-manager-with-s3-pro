import json
import os

CONFIG_FILE = os.path.expanduser("~/.cloud_management_pro_config.json")

class ConfigManager:
    @staticmethod
    def save_config(token, domain=""):
        # Load existing to preserve profiles
        current = ConfigManager.load_config()
        current["token"] = token
        current["domain"] = domain
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(current, f, indent=4)

    @staticmethod
    def save_s3_profile(name, access_key, secret_key, region):
        config = ConfigManager.load_config()
        if "s3_profiles" not in config:
            config["s3_profiles"] = {}
        
        config["s3_profiles"][name] = {
            "aws_access_key": access_key,
            "aws_secret_key": secret_key,
            "aws_region": region
        }
        config["last_selected_profile"] = name
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

    @staticmethod
    def delete_s3_profile(name):
        config = ConfigManager.load_config()
        if "s3_profiles" in config and name in config["s3_profiles"]:
            del config["s3_profiles"][name]
            
            # If we deleted the current profile, clear selection
            if config.get("last_selected_profile") == name:
                config["last_selected_profile"] = ""
                
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            return True
        return False

    @staticmethod
    def save_cf_profile(name, token):
        config = ConfigManager.load_config()
        if "cf_profiles" not in config:
            config["cf_profiles"] = {}
        
        config["cf_profiles"][name] = {
            "token": token
        }
        config["last_selected_cf_profile"] = name
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

    @staticmethod
    def delete_cf_profile(name):
        config = ConfigManager.load_config()
        if "cf_profiles" in config and name in config["cf_profiles"]:
            del config["cf_profiles"][name]
            
            if config.get("last_selected_cf_profile") == name:
                config["last_selected_cf_profile"] = ""
                
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            return True
        return False

    @staticmethod
    def get_cf_profiles():
        config = ConfigManager.load_config()
        return config.get("cf_profiles", {})

    @staticmethod
    def get_s3_profiles():
        config = ConfigManager.load_config()
        return config.get("s3_profiles", {})

    @staticmethod
    def load_config():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    
                # Migration: If old format (keys at root), move to "Default" profile
                if "aws_access_key" in data and "s3_profiles" not in data:
                    # check if they actually have data
                    if data.get("aws_access_key"):
                        data["s3_profiles"] = {
                            "Default": {
                                "aws_access_key": data.pop("aws_access_key", ""),
                                "aws_secret_key": data.pop("aws_secret_key", ""),
                                "aws_region": data.pop("aws_region", "us-east-1")
                            }
                        }
                        data["last_selected_profile"] = "Default"
                
                # Migration for Cloudflare
                if "token" in data and "cf_profiles" not in data:
                    if data.get("token"):
                        data["cf_profiles"] = {
                            "Default": {
                                "token": data.get("token", "")
                            }
                        }
                        data["last_selected_cf_profile"] = "Default"
                        
                with open(CONFIG_FILE, "w") as f:
                     json.dump(data, f, indent=4)
                
                return data
            except Exception:
                return {}
        return {}

    @staticmethod
    def save_wmt_cache(profile_name, data):
        """
        Save WMT/GSC sites and stats to cache for a specific profile.
        data: List of dicts or dict keyed by siteUrl
        """
        config = ConfigManager.load_config()
        if "wmt_cache" not in config:
            config["wmt_cache"] = {}
        
        # Ensure wmt_cache is a dict (migration if it was a list in previous version)
        if isinstance(config["wmt_cache"], list):
             config["wmt_cache"] = {"Default": config["wmt_cache"]}
             
        config["wmt_cache"][profile_name] = data
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

    @staticmethod
    def get_wmt_cache(profile_name):
        config = ConfigManager.load_config()
        cache_data = config.get("wmt_cache", {})
        
        # Migration check
        if isinstance(cache_data, list):
            return cache_data if profile_name == "Default" else []
            
        return cache_data.get(profile_name, [])

    @staticmethod
    def get_gsc_profiles():
        config = ConfigManager.load_config()
        return config.get("gsc_profiles", {})

    @staticmethod
    def save_gsc_profile(name, token_path):
        config = ConfigManager.load_config()
        if "gsc_profiles" not in config:
            config["gsc_profiles"] = {}
            
        config["gsc_profiles"][name] = {"token_path": token_path}
        config["last_selected_gsc_profile"] = name
        
        with open(CONFIG_FILE, "w") as f:
             json.dump(config, f, indent=4)

    @staticmethod
    def delete_gsc_profile(name):
        config = ConfigManager.load_config()
        if "gsc_profiles" in config and name in config["gsc_profiles"]:
            del config["gsc_profiles"][name]
            if config.get("last_selected_gsc_profile") == name:
                config["last_selected_gsc_profile"] = ""
            with open(CONFIG_FILE, "w") as f:
                 json.dump(config, f, indent=4)
            return True
        return False
