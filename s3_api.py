import boto3
import json
from botocore.exceptions import ClientError

class S3API:
    def __init__(self, access_key, secret_key, region):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

    def create_bucket(self, bucket_name, region):
        try:
            if region == "us-east-1":
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def disable_public_access_block(self, bucket_name):
        try:
            self.s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': False,
                    'IgnorePublicAcls': False,
                    'BlockPublicPolicy': False,
                    'RestrictPublicBuckets': False
                }
            )
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def set_public_read_policy(self, bucket_name):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        policy_string = json.dumps(policy)
        try:
            self.s3.put_bucket_policy(Bucket=bucket_name, Policy=policy_string)
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def list_buckets(self):
        try:
            response = self.s3.list_buckets()
            buckets = response.get("Buckets", [])
            # Sort by CreationDate descending (newest first)
            buckets.sort(key=lambda x: x['CreationDate'], reverse=True)
            return {"success": True, "buckets": [b["Name"] for b in buckets]}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def get_bucket_policy(self, bucket_name):
        try:
            response = self.s3.get_bucket_policy(Bucket=bucket_name)
            return {"success": True, "policy": response.get("Policy", "{}")}
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                return {"success": True, "policy": "No policy found"}
            return {"success": False, "error": str(e)}

    def get_public_access_block(self, bucket_name):
        try:
            response = self.s3.get_public_access_block(Bucket=bucket_name)
            return {"success": True, "config": response.get("PublicAccessBlockConfiguration", {})}
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
                return {"success": True, "config": "Disabled (No config)"}
            return {"success": False, "error": str(e)}

    def list_objects(self, bucket_name):
        try:
            response = self.s3.list_objects_v2(Bucket=bucket_name)
            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    "Key": obj['Key'],
                    "LastModified": obj['LastModified'].strftime("%Y-%m-%d %H:%M:%S"),
                    "Size": obj['Size'],
                    "StorageClass": obj['StorageClass']
                })
            return {"success": True, "objects": objects}
        except ClientError as e:
            return {"success": False, "error": str(e)}
    
    def list_objects_hierarchical(self, bucket_name, prefix=""):
        """List objects with hierarchical folder structure for tree display"""
        try:
            response = self.s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            
            # Build hierarchical structure
            folders = {}  # path -> folder info
            files = []    # list of file objects
            
            for obj in response.get('Contents', []):
                key = obj['Key']
                parts = key.split('/')
                
                # Build folder structure
                current_path = ""
                for i, part in enumerate(parts[:-1]):  # All but the last part are folders
                    parent_path = current_path
                    current_path = current_path + part + "/" if current_path else part + "/"
                    
                    if current_path not in folders:
                        folders[current_path] = {
                            "name": part,
                            "path": current_path,
                            "parent": parent_path if parent_path else None,
                            "type": "folder"
                        }
                
                # Add file
                if parts[-1]:  # Not empty (not a folder marker)
                    files.append({
                        "Key": key,
                        "Name": parts[-1],
                        "Path": key,
                        "Parent": current_path if current_path else None,
                        "LastModified": obj['LastModified'],
                        "Size": obj['Size'],
                        "StorageClass": obj['StorageClass'],
                        "type": "file"
                    })
            
            return {
                "success": True, 
                "folders": list(folders.values()),
                "files": files
            }
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def enable_website_hosting(self, bucket_name, index="index.html", error="404.html"):
        try:
            self.s3.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'ErrorDocument': {'Key': error},
                    'IndexDocument': {'Suffix': index}
                }
            )
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def get_bucket_website(self, bucket_name):
        try:
            response = self.s3.get_bucket_website(Bucket=bucket_name)
            return {"success": True, "config": response}
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchWebsiteConfiguration':
                return {"success": True, "config": None}
            return {"success": False, "error": str(e)}

    def object_exists(self, bucket_name, object_name):
        try:
            self.s3.head_object(Bucket=bucket_name, Key=object_name)
            return True
        except ClientError:
            return False

    def upload_file(self, bucket_name, local_path, object_name, overwrite=True):
        import mimetypes
        try:
            if not overwrite and self.object_exists(bucket_name, object_name):
                return {"success": False, "error": "File exists and overwrite is disabled", "skipped": True}

            content_type, _ = mimetypes.guess_type(local_path)
            if content_type is None:
                content_type = 'application/octet-stream'
                
            extra_args = {'ContentType': content_type}
            self.s3.upload_file(local_path, bucket_name, object_name, ExtraArgs=extra_args)
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def upload_directory(self, bucket_name, local_dir, progress_callback=None, overwrite=True):
        import os
        import time
        import mimetypes
        try:
            # 1. Count total files
            total_files = 0
            for root, dirs, files in os.walk(local_dir):
                total_files += len(files)
            
            if total_files == 0:
                return {"success": True, "message": "Structure created but no files found."}

            current_count = 0
            start_time = time.time()
            skipped_count = 0
            
            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    current_count += 1
                    local_path = os.path.join(root, file)
                    # Create object name by preserving relative structure
                    relative_path = os.path.relpath(local_path, local_dir)
                    # On Windows, replace backslashes with forward slashes for S3
                    object_name = relative_path.replace("\\", "/")
                    
                    status = "Uploading"
                    
                    # Check overwrite
                    if not overwrite and self.object_exists(bucket_name, object_name):
                        skipped_count += 1
                        status = "Skipped"
                    else:
                        # Guess mime type
                        content_type, _ = mimetypes.guess_type(local_path)
                        if content_type is None:
                            content_type = 'application/octet-stream'
                            
                        self.s3.upload_file(local_path, bucket_name, object_name, ExtraArgs={'ContentType': content_type})
                    
                    if progress_callback:
                        # Calculate simple stats
                        elapsed = time.time() - start_time
                        avg_speed = current_count / elapsed if elapsed > 0 else 0 # files per second
                        remaining = total_files - current_count
                        
                        progress_data = {
                            "filename": object_name,
                            "current": current_count,
                            "total": total_files,
                            "remaining": remaining,
                            "speed": avg_speed,
                            "status": status
                        }
                        progress_callback(progress_data)
                        
            return {"success": True, "skipped": skipped_count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_file(self, bucket_name, object_name, local_path):
        try:
            self.s3.download_file(bucket_name, object_name, local_path)
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def delete_object(self, bucket_name, object_name):
        try:
            self.s3.delete_object(Bucket=bucket_name, Key=object_name)
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def get_bucket_cors(self, bucket_name):
        try:
            response = self.s3.get_bucket_cors(Bucket=bucket_name)
            return {"success": True, "cors": response.get("CORSRules", [])}
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchCORSConfiguration':
                return {"success": True, "cors": []}
            return {"success": False, "error": str(e)}

    def put_bucket_cors(self, bucket_name, cors_rules):
        try:
            self.s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration={'CORSRules': cors_rules})
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def get_bucket_versioning(self, bucket_name):
        try:
            response = self.s3.get_bucket_versioning(Bucket=bucket_name)
            return {"success": True, "status": response.get("Status", "Disabled")}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def put_bucket_versioning(self, bucket_name, status):
        # status: 'Enabled' or 'Suspended'
        try:
            self.s3.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={'Status': status})
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}

    def delete_bucket(self, bucket_name):
        try:
            self.s3.delete_bucket(Bucket=bucket_name)
            return {"success": True}
        except ClientError as e:
            return {"success": False, "error": str(e)}
