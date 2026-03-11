"""
Storage abstraction for local filesystem and Cloudflare R2.

When R2 is configured (via env vars), files are uploaded to R2 and
public URLs are returned. Otherwise, falls back to local file serving.
"""
import re
from pathlib import Path
from typing import Optional
from loguru import logger

from src.config import settings


def _get_s3_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_file(local_path: str, remote_key: str) -> str:
    """Upload a file to R2. Returns public URL."""
    s3 = _get_s3_client()
    s3.upload_file(local_path, settings.r2_bucket_name, remote_key)
    url = f"{settings.r2_public_url}/{remote_key}"
    logger.debug(f"Uploaded {Path(local_path).name} → {url}")
    return url


def upload_directory(local_dir: str, remote_prefix: str) -> dict[str, str]:
    """
    Upload all files from a local directory to R2.
    Returns {relative_path: public_url} mapping.
    """
    urls: dict[str, str] = {}
    local_path = Path(local_dir)

    for file_path in sorted(local_path.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(local_path)
        remote_key = f"{remote_prefix}/{relative}".replace("\\", "/")
        url = upload_file(str(file_path), remote_key)
        urls[str(relative).replace("\\", "/")] = url

    logger.info(f"Uploaded {len(urls)} files to R2 under prefix '{remote_prefix}'")
    return urls


def move_prefix(old_prefix: str, new_prefix: str) -> None:
    """
    Move all R2 objects from old_prefix to new_prefix
    (copy + delete, since R2/S3 has no native move).
    """
    s3 = _get_s3_client()
    bucket = settings.r2_bucket_name

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=old_prefix + "/")

    keys_to_delete = []
    for page in pages:
        for obj in page.get("Contents", []):
            old_key = obj["Key"]
            new_key = new_prefix + old_key[len(old_prefix):]
            s3.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": old_key},
                Key=new_key,
            )
            keys_to_delete.append({"Key": old_key})

    if keys_to_delete:
        s3.delete_objects(Bucket=bucket, Delete={"Objects": keys_to_delete})
        logger.info(f"Moved {len(keys_to_delete)} objects: {old_prefix} → {new_prefix}")


def rewrite_markdown_image_urls(markdown: str, image_urls: dict[str, str]) -> str:
    """
    Replace relative image paths in markdown with their R2 public URLs.

    Example:
        ![Fig 1](images/fig_001.png)
        →  ![Fig 1](https://pub.r2.dev/area/hash/images/fig_001.png)
    """
    def replace_url(match: re.Match) -> str:
        alt = match.group(1)
        src = match.group(2)
        r2_url = image_urls.get(src)
        if r2_url:
            return f"![{alt}]({r2_url})"
        return match.group(0)  # leave unchanged if not found

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_url, markdown)
