import os
from pathlib import Path

DATA = Path(os.getenv("TSI_DATA_DIR", "private-data")).resolve()
MAX_BYTES = 100 * 1024 * 1024
MAX_SECONDS = 600
MAX_JOBS = 20
RETENTION_SECONDS = 7 * 86400
PIPELINE_VERSION = "0.1.0"


def provider_config():
    key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("TSI_GEMINI_MODEL", "")
    if not key or not model:
        raise RuntimeError("provider_not_configured")
    if os.getenv("TSI_PROVIDER_TERMS_ACCEPTED") != "true":
        raise RuntimeError("provider_terms_not_accepted")
    return key, model
