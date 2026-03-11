from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Literal

class Settings(BaseSettings):
    gemini_api_key: str = ""
    ncbi_api_key: str | None = None
    unpaywall_email: str = ""

    output_dir: Path = Path("./output")
    cache_dir: Path = Path("./cache")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    default_format: Literal["md", "html", "pdf"] = "md"
    cleanup_after: bool = False

    # ── Vercel Blob (opção mais simples — 1 variável, integrado com Vercel) ──
    # Gere em: Vercel Dashboard → Storage → Blob → Connect → .env.local
    blob_read_write_token: str = ""

    # ── Cloudflare R2 (alternativa, mais storage gratuito: 10GB) ─────────────
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_url: str = ""  # e.g. https://pub-abc123.r2.dev

    @property
    def use_vercel_blob(self) -> bool:
        return bool(self.blob_read_write_token)

    @property
    def use_r2(self) -> bool:
        return bool(
            self.r2_access_key_id
            and self.r2_secret_access_key
            and self.r2_bucket_name
            and self.r2_account_id
        )

    @property
    def use_cloud_storage(self) -> bool:
        """True when any cloud storage backend is configured."""
        return self.use_vercel_blob or self.use_r2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
