class S3Syncer:
    def sync_folder_to_s3(self, folder_path: str, bucket_name: str, s3_path: str) -> None:
        print(f"Syncing {folder_path} to s3://{bucket_name}/{s3_path}")

    def sync_folder_from_s3(self, folder_path: str, bucket_name: str, s3_path: str) -> None:
        print(f"Syncing s3://{bucket_name}/{s3_path} to {folder_path}")
