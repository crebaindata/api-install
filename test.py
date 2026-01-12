from __future__ import annotations

import json
import os
import sys
import time
import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from crebain_client import CrebainClient, ApiError

# Crebain API — Client Integration Example (Python)
#
# Steps:
# 1) Load config from environment variables
# 2) Check/onboard an entity (idempotent)
# 3) Print any available files and their signed URLs (if returned)
# 4) Download files from signed URLs (optional)
# 5) List entities (sanity check)
#
# Run:
#   export CREBAIN_API_KEY="ck_live_..."
#   export CREBAIN_BASE_URL="https://<project-ref>.supabase.co/functions/v1/api"
#   export CREBAIN_ANON_KEY="https://<project-ref>.supabase.co/functions/v1/api"
#   python test.py
#
# IMPORTANT: Do NOT paste multi-line blocks into env vars!
# Each export must be a single clean line with no newlines in the value.
#
# Debug (check for hidden chars):
#   python -c 'import os; print(repr(os.getenv("CREBAIN_API_KEY","")))'

CREBAIN_API_KEY = ""  # Set via environment variable or replace with your key
CREBAIN_BASE_URL = ""  # Set via environment variable or replace with your base URL
SUPABASE_ANON_KEY = ""  # Set via environment variable or replace with your Supabase anon key


# =============================================================================
# Configuration 
# =============================================================================

@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    supabase_anon_key: str
    download_dir: str = "downloads"
    timeout_seconds: int = 30

    @staticmethod
    def load() -> "Config":
        api_key = os.getenv("CREBAIN_API_KEY", CREBAIN_API_KEY).strip()
        base_url = os.getenv("CREBAIN_BASE_URL", CREBAIN_BASE_URL).strip().rstrip("/")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY).strip()

        # Validate API key
        if not api_key:
            raise ValueError("Missing CREBAIN_API_KEY environment variable.")
        if not api_key.startswith("ck_"):
            raise ValueError(
                f"Invalid CREBAIN_API_KEY: must start with 'ck_'.\n"
                f"Got: {repr(api_key[:50])}...\n\n"
                f"Fix:\n"
                f'  export CREBAIN_API_KEY="ck_live_your_key_here"'
            )
        if any(c in api_key for c in " \t\r\n"):
            raise ValueError(
                f"Invalid CREBAIN_API_KEY: contains whitespace/newlines.\n"
                f"Got: {repr(api_key[:80])}...\n\n"
                f"Do NOT paste multi-line blocks. Use a single clean line:\n"
                f'  export CREBAIN_API_KEY="ck_live_your_key_here"\n\n'
                f"Debug: python -c 'import os; print(repr(os.getenv(\"CREBAIN_API_KEY\")))'"
            )

        # Validate base URL
        if not base_url:
            raise ValueError("Missing CREBAIN_BASE_URL environment variable.")
        if not base_url.startswith("https://"):
            raise ValueError(
                f"Invalid CREBAIN_BASE_URL: must start with 'https://'.\n"
                f"Got: {repr(base_url[:50])}...\n\n"
                f"Fix:\n"
                f'  export CREBAIN_BASE_URL="https://<project>.supabase.co/functions/v1/api"'
            )
        if any(c in base_url for c in " \t\r\n"):
            raise ValueError(
                f"Invalid CREBAIN_BASE_URL: contains whitespace/newlines.\n"
                f"Got: {repr(base_url[:80])}...\n\n"
                f"Do NOT paste multi-line blocks. Use a single clean line:\n"
                f'  export CREBAIN_BASE_URL="https://<project>.supabase.co/functions/v1/api"'
            )

        return Config(
            api_key=api_key,
            base_url=base_url,
            supabase_anon_key=supabase_anon_key,
            download_dir=os.getenv("CREBAIN_DOWNLOAD_DIR", "downloads"),
            timeout_seconds=int(os.getenv("CREBAIN_TIMEOUT_SECONDS", "30")),
        )


# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("crebain_client_example")


# =============================================================================
# Helpers
# =============================================================================

def safe_filename_from_url(url: str, fallback: str) -> str:
    try:
        name = os.path.basename(urlparse(url).path)
        return name or fallback
    except Exception:
        return fallback


def download_signed_files(files: list, out_dir: str, timeout_seconds: int) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if not files:
        logger.info("📭 No downloadable files returned.")
        return

    logger.info("⬇️  Downloading %d file(s) to %s", len(files), out_path.resolve())

    for idx, f in enumerate(files, start=1):
        signed_url = getattr(f, "signed_url", None) or getattr(f, "download_url", None)
        filename = getattr(f, "filename", None) or safe_filename_from_url(signed_url or "", f"file_{idx}")

        if not signed_url:
            logger.warning("⚠️  Skipping %s (no signed_url).", filename)
            continue

        destination = out_path / filename
        logger.info("➡️  GET %s", signed_url)

        try:
            resp = requests.get(signed_url, stream=True, timeout=timeout_seconds)
            if resp.status_code != 200:
                logger.error("❌ Download failed for %s (HTTP %s).", filename, resp.status_code)
                continue

            with destination.open("wb") as fp:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        fp.write(chunk)

            logger.info("✅ Downloaded %s (%d bytes).", filename, destination.stat().st_size)

        except Exception:
            logger.exception("❌ Download exception for %s.", filename)


class TracedCrebainClient(CrebainClient):
    """
    Small wrapper around the SDK to log:
    - method
    - full URL
    - request payload (safe / truncated)
    - response status + request_id (when available)

    It relies on the SDK using a `_request` method internally.
    """

    def _request(self, method: str, path: str, params=None, json=None, headers=None):
        full_url = self.base_url.rstrip("/") + path  # path is like "/v1/entity/check"
        logger.info("────────────────────────────────────────────────────────")
        logger.info("➡️  %s %s", method, full_url)

        if headers and headers.get("Idempotency-Key"):
            logger.info("   Idempotency-Key: %s", headers.get("Idempotency-Key"))

        if json is not None:
            import json as json_module
            payload_preview = json_module.dumps(json)[:800]
            logger.info("   Payload: %s%s", payload_preview, "..." if len(payload_preview) >= 800 else "")

        t0 = time.time()
        data, request_id = super()._request(method, path, params=params, json=json, headers=headers)
        ms = int((time.time() - t0) * 1000)

        logger.info("⬅️  OK (%d ms) request_id=%s", ms, request_id)
        return data, request_id


# =============================================================================
# Example flow (step-by-step)
# =============================================================================

def run_example() -> None:
    cfg = Config.load()

    # Use traced client so we print the explicit URLs for each request
    client = TracedCrebainClient(api_key=cfg.api_key, base_url=cfg.base_url, supabase_anon_key=cfg.supabase_anon_key)

    target = {
        "external_entity_id": "stenn",
        "name": "Stenn Technologies",
        "metadata": {"sector": "FinTech", "example_run": True},
    }

    logger.info("✅ Loaded config")
    logger.info("   Base URL: %s", cfg.base_url)
    logger.info("   Download dir: %s", cfg.download_dir)

    try:
        # STEP 1 — Entity check / onboarding
        logger.info("\nSTEP 1) Entity check / onboarding")
        result = client.check_entity(
            external_entity_id=target["external_entity_id"],
            name=target["name"],
            metadata=target["metadata"],
            force=False,
            adverse_news_only=False,
            idempotency_key=f"check-{target['external_entity_id']}-v1",
        )

        logger.info("✅ Entity check result")
        logger.info("   entity_id=%s", result.entity_id)
        logger.info("   new_company=%s", result.new_company)
        logger.info("   request_submitted=%s", result.request_submitted)
        if getattr(result, "request_id", None):
            logger.info("   request_id=%s", result.request_id)

        # STEP 2 — Files available immediately (if any)
        logger.info("\nSTEP 2) Files currently available (if returned)")
        files_available = getattr(result, "files_available", []) or []
        logger.info("   files_available=%d", len(files_available))

        for f in files_available:
            fid = getattr(f, "file_id", None) or getattr(f, "id", None) or "unknown"
            fn = getattr(f, "filename", None) or getattr(f, "name", None) or "unknown"
            mt = getattr(f, "mime_type", None) or "unknown"
            surl = getattr(f, "signed_url", None) or getattr(f, "download_url", None)

            logger.info("   - %s | mime=%s | file_id=%s", fn, mt, fid)
            if surl:
                logger.info("     signed_url=%s...", surl[:100])

        # STEP 3 — Download files from signed URLs (optional)
        logger.info("\nSTEP 3) Download available files (if signed URLs exist)")
        download_signed_files(files_available, out_dir=cfg.download_dir, timeout_seconds=cfg.timeout_seconds)

        # STEP 4 — List entities (sanity check)
        logger.info("\nSTEP 4) List entities (sanity check)")
        entities_page = client.list_entities(limit=20)
        logger.info("✅ Returned %d entities (showing up to 20)", len(entities_page.entities))
        for e in entities_page.entities:
            eid = getattr(e, "entity_id", None) or getattr(e, "id", None)
            logger.info("   - %s | external=%s | id=%s",
                        getattr(e, "name", None),
                        getattr(e, "external_entity_id", None),
                        eid)

        logger.info("\n🎉 Finished successfully.")

    except ApiError as e:
        logger.error("────────────────────────────────────────────────────────")
        logger.error("❌ API ERROR")
        logger.error("   status=%s", getattr(e, "status_code", None))
        logger.error("   code=%s", getattr(e, "code", None))
        logger.error("   request_id=%s", getattr(e, "request_id", None))
        logger.error("   message=%s", getattr(e, "message", str(e)))
        if getattr(e, "response_body", None):
            logger.error("   response_body=%s", getattr(e, "response_body", None))
        raise

    except Exception:
        logger.exception("⚠️ Unexpected exception")
        raise


if __name__ == "__main__":
    run_example()
    
