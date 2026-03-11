"""
Storage abstraction with support for Vercel Blob, Cloudflare R2, and local filesystem.

Priority:
  1. Vercel Blob  (BLOB_READ_WRITE_TOKEN) — 1 env var, integrated with Vercel
  2. Cloudflare R2 (R2_* vars)           — 10 GB free, zero egress cost
  3. Local filesystem                     — development fallback
"""
import re
import mimetypes
from pathlib import Path
from loguru import logger

from src.config import settings


# ── Vercel Blob ───────────────────────────────────────────────────────────────

def _vercel_upload(local_path: str, pathname: str) -> str:
    """Upload a file to Vercel Blob. Returns public URL."""
    import httpx

    mime = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
    with open(local_path, "rb") as f:
        content = f.read()

    resp = httpx.put(
        f"https://blob.vercel-storage.com/{pathname}",
        content=content,
        headers={
            "Authorization": f"Bearer {settings.blob_read_write_token}",
            "x-content-type": mime,
            "x-cache-control-max-age": "31536000",  # 1 year
        },
        timeout=60,
        params={"access": "public"},
    )
    resp.raise_for_status()
    url = resp.json()["url"]
    logger.debug(f"Vercel Blob: {Path(local_path).name} → {url}")
    return url


def _vercel_list(prefix: str) -> list[dict]:
    """List all blobs under a prefix."""
    import httpx

    blobs = []
    cursor = None
    while True:
        params: dict = {"prefix": prefix, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        resp = httpx.get(
            "https://blob.vercel-storage.com",
            headers={"Authorization": f"Bearer {settings.blob_read_write_token}"},
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        blobs.extend(data.get("blobs", []))
        if not data.get("hasMore"):
            break
        cursor = data.get("cursor")
    return blobs


def _vercel_delete(urls: list[str]) -> None:
    """Delete blobs by their public URLs."""
    import httpx
    if not urls:
        return
    resp = httpx.delete(
        "https://blob.vercel-storage.com",
        headers={"Authorization": f"Bearer {settings.blob_read_write_token}"},
        json={"urls": urls},
        timeout=30,
    )
    resp.raise_for_status()


def _vercel_move_prefix(old_prefix: str, new_prefix: str) -> None:
    """
    Move all Vercel Blob objects from old_prefix to new_prefix.
    Vercel Blob has no native copy, so we download + re-upload + delete.
    """
    import httpx

    blobs = _vercel_list(old_prefix)
    if not blobs:
        return

    urls_to_delete = []
    for blob in blobs:
        old_url = blob["url"]
        old_pathname = blob["pathname"]
        new_pathname = new_prefix + old_pathname[len(old_prefix):]

        # Download and re-upload
        content = httpx.get(old_url, timeout=60).content
        mime = mimetypes.guess_type(old_pathname)[0] or "application/octet-stream"

        resp = httpx.put(
            f"https://blob.vercel-storage.com/{new_pathname}",
            content=content,
            headers={
                "Authorization": f"Bearer {settings.blob_read_write_token}",
                "x-content-type": mime,
            },
            params={"access": "public"},
            timeout=60,
        )
        resp.raise_for_status()
        urls_to_delete.append(old_url)

    _vercel_delete(urls_to_delete)
    logger.info(f"Vercel Blob: moved {len(blobs)} objects: {old_prefix} → {new_prefix}")


# ── Cloudflare R2 ─────────────────────────────────────────────────────────────

def _r2_client():
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


def _r2_upload(local_path: str, remote_key: str) -> str:
    s3 = _r2_client()
    s3.upload_file(local_path, settings.r2_bucket_name, remote_key)
    url = f"{settings.r2_public_url}/{remote_key}"
    logger.debug(f"R2: {Path(local_path).name} → {url}")
    return url


def _r2_move_prefix(old_prefix: str, new_prefix: str) -> None:
    s3 = _r2_client()
    bucket = settings.r2_bucket_name
    paginator = s3.get_paginator("list_objects_v2")
    keys_to_delete = []
    for page in paginator.paginate(Bucket=bucket, Prefix=old_prefix + "/"):
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
        logger.info(f"R2: moved {len(keys_to_delete)} objects: {old_prefix} → {new_prefix}")


# ── Public API ────────────────────────────────────────────────────────────────

def upload_file(local_path: str, remote_key: str) -> str:
    """Upload a file to configured cloud storage. Returns public URL."""
    if settings.use_vercel_blob:
        return _vercel_upload(local_path, remote_key)
    return _r2_upload(local_path, remote_key)


def upload_directory(local_dir: str, remote_prefix: str) -> dict[str, str]:
    """
    Upload all files from a local directory to cloud storage.
    Returns {relative_path: public_url} mapping.
    """
    urls: dict[str, str] = {}
    local_path = Path(local_dir)
    for file_path in sorted(local_path.rglob("*")):
        if not file_path.is_file():
            continue
        relative = str(file_path.relative_to(local_path)).replace("\\", "/")
        remote_key = f"{remote_prefix}/{relative}"
        urls[relative] = upload_file(str(file_path), remote_key)
    logger.info(f"Uploaded {len(urls)} files under '{remote_prefix}'")
    return urls


def move_prefix(old_prefix: str, new_prefix: str) -> None:
    """Move all cloud storage objects from old_prefix to new_prefix."""
    if settings.use_vercel_blob:
        _vercel_move_prefix(old_prefix, new_prefix)
    elif settings.use_r2:
        _r2_move_prefix(old_prefix, new_prefix)


def rewrite_markdown_image_urls(markdown: str, image_urls: dict[str, str]) -> str:
    """
    Replace relative image paths in markdown with cloud storage public URLs.

    Example:
        ![Fig 1](images/fig_001.png)
        → ![Fig 1](https://abc.public.blob.vercel-storage.com/…/fig_001.png)
    """
    def replace_url(match: re.Match) -> str:
        alt = match.group(1)
        src = match.group(2)
        cloud_url = image_urls.get(src)
        if cloud_url:
            return f"![{alt}]({cloud_url})"
        return match.group(0)

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_url, markdown)
