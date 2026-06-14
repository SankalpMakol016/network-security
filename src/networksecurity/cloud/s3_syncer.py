import subprocess


class S3Syncer:

    def sync_folder_to_s3(self,folder_path: str,aws_bucket_url: str) -> None:
        command = [
            "aws",
            "s3",
            "sync",
            folder_path,
            aws_bucket_url
        ]
        subprocess.run(command, check=True)
        print(f"Synced {folder_path} -> {aws_bucket_url}")

    def sync_folder_from_s3(self,folder_path: str,aws_bucket_url: str) -> None:
        command = [
            "aws",
            "s3",
            "sync",
            aws_bucket_url,
            folder_path
        ]
        subprocess.run(command, check=True)
        print(f"Synced {aws_bucket_url} -> {folder_path}")