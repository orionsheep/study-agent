from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    content_type: str
    sha256: str
    size_bytes: int
    public_url: str | None = None


def safe_object_part(value: str, fallback: str = "artifact") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._/-]+", "-", str(value or "").strip()).strip("-./")
    return cleaned[:140] or fallback


def artifact_object_key(*, kind: str, artifact_id: str, filename: str | None = None) -> str:
    suffix = safe_object_part(filename or "", "")
    base = f"artifacts/{safe_object_part(kind, 'artifact')}/{safe_object_part(artifact_id, 'artifact')}"
    return f"{base}/{suffix}" if suffix else base


class ObjectStorage:
    """S3-compatible artifact storage with an explicit development fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.local_root = self.settings.data_dir / "artifacts"

    @property
    def s3_configured(self) -> bool:
        return bool(
            self.settings.object_storage_bucket
            and self.settings.object_storage_access_key_id
            and self.settings.object_storage_secret_access_key
        )

    @property
    def production_requires_s3(self) -> bool:
        return self.settings.app_env.lower() == "production"

    def status(self) -> dict[str, Any]:
        if self.s3_configured:
            return {
                "status": "ready",
                "backend": "s3_compatible",
                "bucket": self.settings.object_storage_bucket,
                "endpoint_configured": bool(self.settings.object_storage_endpoint),
                "public_base_url_configured": bool(self.settings.object_storage_public_base_url),
            }
        if self.production_requires_s3:
            return {
                "status": "blocked_missing_config",
                "backend": "s3_compatible",
                "reason": "Production requires OBJECT_STORAGE_BUCKET/ACCESS_KEY_ID/SECRET_ACCESS_KEY.",
            }
        return {
            "status": "ready",
            "backend": "local_development",
            "reason": "Development fallback writes artifacts under .data/artifacts; production must use S3-compatible storage.",
            "path": str(self.local_root),
        }

    def _client(self) -> Any:
        try:
            import boto3
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("boto3 is required for S3-compatible object storage.") from exc
        kwargs: dict[str, Any] = {
            "aws_access_key_id": self.settings.object_storage_access_key_id,
            "aws_secret_access_key": self.settings.object_storage_secret_access_key,
            "region_name": self.settings.object_storage_region or None,
        }
        if self.settings.object_storage_endpoint:
            kwargs["endpoint_url"] = self.settings.object_storage_endpoint
        return boto3.client("s3", **kwargs)

    def _local_path(self, object_key: str) -> Path:
        key = safe_object_part(object_key, "artifact")
        path = (self.local_root / key).resolve()
        root = self.local_root.resolve()
        if root not in path.parents and path != root:
            raise ValueError("invalid object key")
        return path

    def public_url(self, object_key: str) -> str | None:
        base = self.settings.object_storage_public_base_url.rstrip("/")
        if not base:
            return None
        return f"{base}/{safe_object_part(object_key)}"

    def local_file_path(self, object_key: str) -> str:
        return str(self._local_path(object_key))

    def put_bytes(self, *, object_key: str, data: bytes, content_type: str) -> StoredObject:
        digest = hashlib.sha256(data).hexdigest()
        if self.s3_configured:
            self._client().put_object(
                Bucket=self.settings.object_storage_bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type,
            )
        else:
            if self.production_requires_s3:
                raise RuntimeError("Object storage is not configured for production.")
            path = self._local_path(object_key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return StoredObject(
            object_key=object_key,
            content_type=content_type,
            sha256=digest,
            size_bytes=len(data),
            public_url=self.public_url(object_key),
        )

    def get_bytes(self, object_key: str) -> tuple[bytes, str]:
        if self.s3_configured:
            response = self._client().get_object(Bucket=self.settings.object_storage_bucket, Key=object_key)
            body = response["Body"].read()
            return body, str(response.get("ContentType") or "application/octet-stream")
        if self.production_requires_s3:
            raise RuntimeError("Object storage is not configured for production.")
        return self._local_path(object_key).read_bytes(), "application/octet-stream"
