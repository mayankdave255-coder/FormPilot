"""Private object storage with a local adapter for development."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


_backend = "local"
_root = Path("backend/data").resolve()
_bucket = ""
_client: Any = None


def init_storage(local_root: Path) -> None:
    global _backend, _root, _bucket, _client
    _root = local_root.resolve()
    _bucket = os.getenv("S3_BUCKET", "").strip()
    _backend = os.getenv("OBJECT_STORAGE_BACKEND", "s3" if _bucket else "local").strip().lower()
    if _backend not in {"local", "s3"}:
        raise RuntimeError("OBJECT_STORAGE_BACKEND must be 'local' or 's3'.")
    if _backend == "local":
        if os.getenv("APP_ENV", "development").lower() == "production":
            print("[formpilot] WARNING: object storage is not configured; production uploads and draft creation are disabled.")
        return
    required = [name for name in ("S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY") if not os.getenv(name, "").strip()]
    if required:
        raise RuntimeError("Set S3_BUCKET, S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY to enable object storage.")
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError("Install the boto3 dependency to use S3-compatible object storage.") from exc
    endpoint = os.getenv("S3_ENDPOINT_URL", "").strip() or None
    region = os.getenv("S3_REGION", "auto" if endpoint else "us-east-1").strip()
    _client = boto3.client(
        "s3", endpoint_url=endpoint, region_name=region,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      retries={"max_attempts": 3, "mode": "standard"}),
    )
    print(f"[formpilot] file_storage_backend=s3 bucket={_bucket}")


def backend_name() -> str:
    return _backend


def ping() -> bool:
    if _backend == "local":
        return True
    try:
        _client.head_bucket(Bucket=_bucket)
        return True
    except Exception as exc:
        print(f"file_storage_error operation=head_bucket error={type(exc).__name__}")
        return False


def _local_path(key: str) -> Path:
    path = (_root / key).resolve()
    if not path.is_relative_to(_root):
        raise ValueError("Invalid object key.")
    return path


def put_object(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    if _backend == "s3":
        _client.put_object(Bucket=_bucket, Key=key, Body=data, ContentType=content_type)
        return
    path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def get_object(key: str) -> bytes:
    if _backend == "s3":
        response = _client.get_object(Bucket=_bucket, Key=key)
        with response["Body"] as body:
            return body.read()
    return _local_path(key).read_bytes()


def delete_object(key: str) -> None:
    if _backend == "s3":
        _client.delete_object(Bucket=_bucket, Key=key)
        return
    _local_path(key).unlink(missing_ok=True)


def copy_object(source_key: str, target_key: str, content_type: str = "application/octet-stream") -> None:
    if _backend == "s3":
        _client.copy_object(Bucket=_bucket, CopySource={"Bucket": _bucket, "Key": source_key},
                            Key=target_key, ContentType=content_type, MetadataDirective="REPLACE")
        return
    put_object(target_key, get_object(source_key), content_type)
