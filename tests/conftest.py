import pytest

from operia_crm.config.settings import settings
from operia_crm.database.db import init_db


@pytest.fixture()
def isolated_env(tmp_path):
    original_db = settings.db_path
    original_attachments = settings.attachments_dir
    original_backups = settings.backups_dir
    object.__setattr__(settings, "db_path", tmp_path / "test.db")
    object.__setattr__(settings, "attachments_dir", tmp_path / "attachments")
    object.__setattr__(settings, "backups_dir", tmp_path / "backups")
    init_db()
    try:
        yield tmp_path
    finally:
        object.__setattr__(settings, "db_path", original_db)
        object.__setattr__(settings, "attachments_dir", original_attachments)
        object.__setattr__(settings, "backups_dir", original_backups)
