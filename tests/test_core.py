from pathlib import Path

import pytest

from operia_crm.config.settings import settings
from operia_crm.database.db import init_db
from operia_crm.services.core import (
    ALLOWED_EXTENSIONS,
    _is_blank,
    calculate_score,
    create_lead,
    create_proposal,
    dedupe_row,
    import_deduped_leads,
    normalize_phone,
    normalize_text,
    save_attachment,
)


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


class _FakeRow:
    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return self._data


class _FakeDf:
    def __init__(self, rows):
        self._rows = rows

    def __len__(self):
        return len(self._rows)

    def iterrows(self):
        for i, row in enumerate(self._rows):
            yield i, _FakeRow(row)


def test_dedupe_strong_phone():
    row = {"phone": "(11) 99999-1111"}
    existing = [{"phone": "11999991111", "whatsapp": "", "email": "", "name": "A", "city": ""}]
    assert dedupe_row(row, existing) == "duplicado forte"


def test_normalize_text_handles_blank_and_non_string_values():
    assert normalize_text(None) == ""
    assert normalize_text(float("nan")) == ""
    assert normalize_text("nan") == ""
    assert normalize_text("none") == ""
    assert normalize_text("<NA>") == ""
    assert normalize_text("  Clínica  ") == "clínica"
    assert normalize_text(123) == "123"
    assert normalize_text(12.3) == "12.3"


def test_normalize_phone_handles_blank_and_non_string_values():
    assert normalize_phone(None) == ""
    assert normalize_phone(float("nan")) == ""
    assert normalize_phone("nan") == ""
    assert normalize_phone("(37) 99999-0000") == "37999990000"
    assert normalize_phone("37 99999-0000") == "37999990000"
    assert normalize_phone(37999990000) == "37999990000"
    assert normalize_phone(37999990000.0) == "37999990000"


def test_is_blank_handles_empty_and_valid_values():
    assert _is_blank(None) is True
    assert _is_blank(float("nan")) is True
    assert _is_blank("") is True
    assert _is_blank("nan") is True
    assert _is_blank("none") is True
    assert _is_blank("<NA>") is True
    assert _is_blank(0) is False
    assert _is_blank("0") is False


def test_blank_normalization_handles_pandas_na_when_available():
    pd = pytest.importorskip("pandas")

    assert _is_blank(pd.NA) is True
    assert normalize_text(pd.NA) == ""
    assert normalize_phone(pd.NA) == ""


def test_dedupe_row_with_nan_fields_does_not_break():
    row = {"name": "Contato", "email": float("nan"), "phone": float("nan"), "whatsapp": float("nan"), "city": float("nan")}
    existing = [{"phone": "", "whatsapp": "", "email": "", "name": "Outro", "city": ""}]
    assert dedupe_row(row, existing) == "não duplicado"


def test_dedupe_row_keeps_strong_and_probable_duplicate_rules():
    existing = [{"phone": "37999990000", "whatsapp": "", "email": "lead@example.com", "name": "Clínica Boa", "city": "Divinópolis"}]
    assert dedupe_row({"phone": "(37) 99999-0000"}, existing) == "duplicado forte"
    assert dedupe_row({"email": " lead@example.com "}, existing) == "duplicado forte"
    assert dedupe_row({"name": " clínica boa ", "city": " Divinópolis "}, existing) == "duplicado provável"


def test_import_deduped_leads_with_optional_nan_fields_imports_valid_contact(monkeypatch):
    captured = []
    monkeypatch.setattr("operia_crm.services.core.create_lead", lambda payload: captured.append(payload) or 1)

    df = _FakeDf([
        {"name": "Ana", "email": float("nan"), "whatsapp": "(37) 99999-0000", "phone": float("nan"), "city": float("nan"), "company": float("nan"), "segment": float("nan"), "notes": float("nan")},
        {"name": "Bia", "email": "bia@example.com", "whatsapp": float("nan"), "phone": float("nan"), "city": "BH", "company": float("nan")},
        {"name": "Sem Contato", "email": float("nan"), "whatsapp": float("nan"), "phone": float("nan"), "city": "BH"},
    ])
    summary = import_deduped_leads(df, existing=[])
    assert summary["importados"] == 2
    assert summary["ignorados_sem_contato"] == 1
    assert captured[0]["name"] == "Ana"
    assert captured[0]["whatsapp"] == "(37) 99999-0000"
    assert captured[1]["email"] == "bia@example.com"
    assert captured[1]["phone"] is None
    for payload in captured:
        optional_values = [payload.get("company"), payload.get("city"), payload.get("segment"), payload.get("notes"), payload.get("phone"), payload.get("whatsapp"), payload.get("email")]
        assert "nan" not in {str(value).lower() for value in optional_values}


def test_import_recomputes_dedupe_even_when_analysis_dedupe_is_present(monkeypatch):
    captured = []
    monkeypatch.setattr("operia_crm.services.core.create_lead", lambda payload: captured.append(payload) or len(captured))

    df = _FakeDf([
        {"name": "Clínica Alfa", "phone": "37999990000", "email": "", "dedupe": "não duplicado"},
        {"name": "Clínica Alfa Duplicada", "phone": "37999990000", "email": "", "dedupe": "não duplicado"},
    ])

    summary = import_deduped_leads(df, existing=[])

    assert summary["total_linhas"] == 2
    assert summary["importados"] == 1
    assert summary["ignorados_duplicidade"] == 1
    assert [payload["name"] for payload in captured] == ["Clínica Alfa"]


def test_import_recomputes_dedupe_against_current_existing_state(monkeypatch):
    captured = []
    monkeypatch.setattr("operia_crm.services.core.create_lead", lambda payload: captured.append(payload) or 1)
    existing = [{"phone": "37999990000", "whatsapp": "", "email": "", "name": "Lead Criado Depois", "city": ""}]

    df = _FakeDf([
        {"name": "Lead vindo da análise antiga", "phone": "37999990000", "email": "", "dedupe": "não duplicado"},
    ])

    summary = import_deduped_leads(df, existing=existing)

    assert summary["importados"] == 0
    assert summary["ignorados_duplicidade"] == 1
    assert captured == []


def test_score_bounds():
    s = calculate_score({"phone": "11", "email": "a@a.com", "status": "Negociação", "next_followup": "2026-01-01"})
    assert 0 <= s <= 100


def test_proposal_sequence_starts_and_increments(isolated_env):
    lead_id = create_lead({"name": "Lead 1", "origin": "Site", "status": "Novo lead"})
    first = create_proposal(lead_id, 100.0, "Primeira", None)
    second = create_proposal(lead_id, 200.0, "Segunda", None)
    assert first == "PROP-0001"
    assert second == "PROP-0002"


def test_proposal_sequence_persists_in_sqlite(isolated_env):
    lead_id = create_lead({"name": "Lead Persist", "origin": "Site", "status": "Novo lead"})
    assert create_proposal(lead_id, 50.0, "A", None) == "PROP-0001"
    assert create_proposal(lead_id, 75.0, "B", None) == "PROP-0002"

    # Reabre fluxo com o mesmo SQLite para validar persistência da sequência.
    assert create_proposal(lead_id, 90.0, "C", None) == "PROP-0003"


@pytest.mark.parametrize("filename", ["ok.pdf", "ok.docx", "ok.xlsx", "ok.png", "ok.jpg", "ok.jpeg"])
def test_attachment_allowed_extensions(isolated_env, filename):
    lead_id = create_lead({"name": "Lead Attach", "origin": "Google", "status": "Novo lead"})
    out = save_attachment(lead_id, filename, b"dummy")
    assert out.exists()
    assert out.suffix.lower() in ALLOWED_EXTENSIONS


@pytest.mark.parametrize(
    "filename",
    [
        "virus.exe",
        "script.bat",
        "shell.cmd",
        "hack.ps1",
        "auto.js",
        "macro.vbs",
        "installer.msi",
        "compressed.zip",
        "compressed.rar",
        "compressed.7z",
        "unknown.xyz",
    ],
)
def test_attachment_blocked_extensions(isolated_env, filename):
    lead_id = create_lead({"name": "Lead Block", "origin": "Google", "status": "Novo lead"})
    with pytest.raises(ValueError):
        save_attachment(lead_id, filename, b"dummy")


def test_security_gitignore_and_gemini_env_usage():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "\n.env\n" in f"\n{gitignore}\n"
    assert "*.db" in gitignore and "*.sqlite" in gitignore
    assert "attachments/" in gitignore
    assert "backups/" in gitignore
    assert "data/" in gitignore

    settings_src = Path("src/operia_crm/config/settings.py").read_text(encoding="utf-8")
    assert "os.getenv('GEMINI_API_KEY'" in settings_src
