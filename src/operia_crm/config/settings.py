from dataclasses import dataclass
from pathlib import Path
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

@dataclass(frozen=True)
class Settings:
    db_path: Path = Path(os.getenv('OPERIA_DB_PATH', 'data/operia_crm.db'))
    attachments_dir: Path = Path(os.getenv('OPERIA_ATTACHMENTS_DIR', 'attachments'))
    backups_dir: Path = Path(os.getenv('OPERIA_BACKUPS_DIR', 'backups'))
    gemini_api_key: str | None = os.getenv('GEMINI_API_KEY') or None

settings = Settings()
