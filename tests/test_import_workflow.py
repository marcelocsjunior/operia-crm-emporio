from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from operia_crm.services.import_workflow import (
    SERVER_INBOX_SOURCE,
    UPLOAD_BROWSER_SOURCE,
    analyze_import_dataframe,
    build_import_package,
    build_import_diagnostics,
    build_import_file_info,
    ensure_import_inbox_dir,
    file_sha256,
    list_import_inbox_files,
    load_import_inbox_file,
)


def test_file_sha256_stable_hash():
    content = b"nome,whatsapp\nAna,37999990000\n"
    assert file_sha256(content) == file_sha256(content)
    assert file_sha256(content) != file_sha256(content + b"x")


def test_build_import_file_info_returns_name_size_and_type():
    content = b"abc"
    info = build_import_file_info("leads.csv", content)
    assert info["file_name"] == "leads.csv"
    assert info["size"] == 3
    assert info["file_type"] == "CSV"
    assert info["sha256"] == file_sha256(content)


def test_analyze_import_dataframe_recognizes_valid_columns():
    df = pd.DataFrame([{"nome": "Ana", "empresa": "Clínica", "whatsapp": "37999990000"}])
    analysis = analyze_import_dataframe(df, [])
    recognized = {item["column"]: item["field"] for item in analysis["recognized_columns"]}
    assert recognized["nome"] == "name"
    assert recognized["empresa"] == "company"
    assert recognized["whatsapp"] == "whatsapp"


def test_analyze_import_dataframe_lists_ignored_columns():
    df = pd.DataFrame([{"nome": "Ana", "whatsapp": "37999990000", "extra": "valor"}])
    analysis = analyze_import_dataframe(df, [])
    assert analysis["ignored_columns"] == ["extra"]


def test_name_and_valid_whatsapp_is_ok_with_alert():
    df = pd.DataFrame([{"nome": "Ana", "whatsapp": "37999990000"}])
    analysis = analyze_import_dataframe(df, [])
    row = analysis["rows"][0]
    assert row["acao_prevista"] == "Importar"
    assert row["status_analise"] == "OK com alerta"
    assert "contato válido" in row["motivo"]
    assert analysis["summary"]["prontas_para_importar"] == 1


def test_name_without_phone_whatsapp_or_email_is_ignored_without_contact():
    df = pd.DataFrame([{"nome": "Sem Contato"}])
    analysis = analyze_import_dataframe(df, [])
    row = analysis["rows"][0]
    assert row["status_analise"] == "Ignorada"
    assert row["reason_key"] == "sem_contato"
    assert row["motivo"] == "Sem telefone, WhatsApp ou e-mail."
    assert analysis["summary"]["ignoradas_sem_contato"] == 1


def test_row_without_name_is_ignored_without_name():
    df = pd.DataFrame([{"nome": "", "email": "lead@example.com"}])
    analysis = analyze_import_dataframe(df, [])
    row = analysis["rows"][0]
    assert row["status_analise"] == "Ignorada"
    assert row["reason_key"] == "sem_nome"
    assert analysis["summary"]["ignoradas_sem_nome"] == 1


def test_strong_duplicate_is_identified():
    existing = [{"phone": "37999990000", "whatsapp": "", "email": "", "name": "Ana", "city": "BH"}]
    df = pd.DataFrame([{"nome": "Ana Nova", "telefone": "(37) 99999-0000"}])
    analysis = analyze_import_dataframe(df, existing)
    row = analysis["rows"][0]
    assert row["dedupe"] == "duplicado forte"
    assert row["status_analise"] == "Ignorada"
    assert analysis["summary"]["duplicadas_fortes"] == 1


def test_extra_columns_do_not_break_analysis():
    df = pd.DataFrame([{"nome": "Ana", "whatsapp": "37999990000", "campanha": "Maio"}])
    analysis = analyze_import_dataframe(df, [])
    assert analysis["summary"]["total_linhas"] == 1
    assert analysis["ignored_columns"] == ["campanha"]


def test_nan_fields_do_not_break_analysis():
    df = pd.DataFrame([{"nome": "Ana", "email": math.nan, "whatsapp": "37999990000", "telefone": math.nan}])
    analysis = analyze_import_dataframe(df, [])
    row = analysis["rows"][0]
    assert row["email"] == ""
    assert row["telefone"] == ""
    assert row["acao_prevista"] == "Importar"


def test_diagnostics_returns_clear_message_for_invalid_file():
    diagnostics = build_import_diagnostics("leads.csv", b"empresa,email\nAcme,a@x.com\n", [])
    assert diagnostics["success"] is False
    assert diagnostics["message"] == "Não foi possível ler o arquivo."
    assert "Motivo provável:" in diagnostics["reason"]
    assert "Ação recomendada:" in diagnostics["recommendation"]
    assert "Traceback" not in diagnostics["reason"]


def test_analysis_does_not_write_during_diagnostics(monkeypatch):
    calls = []

    def fake_create_lead(payload):
        calls.append(payload)
        raise AssertionError("analysis must not write")

    monkeypatch.setattr("operia_crm.services.core.create_lead", fake_create_lead)
    diagnostics = build_import_diagnostics("leads.csv", b"nome,whatsapp\nAna,37999990000\n", [])
    assert diagnostics["success"] is True
    assert calls == []


def test_final_import_still_uses_import_deduped_leads_in_app():
    app_source = Path("app.py").read_text()
    assert "Confirmar importação" in app_source
    assert "import_deduped_leads(import_df" in app_source


def test_import_uploader_uses_stable_key_and_explicit_clear():
    app_source = Path("app.py").read_text()
    import_tab = app_source.split('with tab3:', 1)[1].split('with tab4:', 1)[0]

    assert 'uploader_key = "import_file_uploader"' in import_tab
    assert 'key=uploader_key' in import_tab
    assert '"Selecionar no navegador"' in import_tab
    assert '"Usar arquivo salvo no servidor"' in import_tab
    assert 'import_workflow_uploader_version' not in import_tab
    assert 'key=f"import_file_uploader_' not in import_tab
    assert '"Selecionar arquivo CSV ou XLSX"' in import_tab
    assert '"Limpar arquivo selecionado"' in import_tab
    assert 'st.session_state.pop(uploader_key, None)' in import_tab


def test_import_selection_message_and_diagnostic_guard():
    app_source = Path("app.py").read_text()
    import_tab = app_source.split('with tab3:', 1)[1].split('with tab4:', 1)[0]

    assert "Arquivo selecionado. Revise o diagnóstico antes de importar." in import_tab
    assert "Arquivo carregado da pasta do servidor. Revise o diagnóstico antes de importar." in import_tab
    assert 'disabled=package is None' in import_tab
    assert "if analyze_clicked and package is not None:" in import_tab


def test_import_inbox_directory_is_created(tmp_path):
    inbox = tmp_path / "imports" / "inbox"
    assert not inbox.exists()
    assert ensure_import_inbox_dir(inbox) == inbox
    assert inbox.is_dir()


def test_import_inbox_lists_only_safe_csv_and_xlsx_files(tmp_path):
    inbox = ensure_import_inbox_dir(tmp_path / "imports" / "inbox")
    (inbox / "leads.csv").write_text("nome,email\nAna,a@x.com\n")
    (inbox / "planilha.xlsx").write_bytes(b"fake")
    (inbox / ".hidden.csv").write_text("x")
    (inbox / "~$planilha.xlsx").write_bytes(b"x")
    (inbox / "upload.tmp").write_text("x")
    (inbox / "notes.txt").write_text("x")
    (inbox / "subdir").mkdir()
    (inbox / "subdir" / "nested.csv").write_text("x")

    assert list_import_inbox_files(inbox) == ["leads.csv", "planilha.xlsx"]


def test_import_inbox_rejects_arbitrary_paths(tmp_path):
    inbox = ensure_import_inbox_dir(tmp_path / "imports" / "inbox")
    (inbox / "leads.csv").write_text("nome,email\nAna,a@x.com\n")
    outside = tmp_path / "outside.csv"
    outside.write_text("nome,email\nBia,b@x.com\n")

    for unsafe in ["../outside.csv", str(outside), "subdir/nested.csv", ".hidden.csv", "notes.txt"]:
        try:
            load_import_inbox_file(unsafe, inbox)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe path accepted: {unsafe}")


def test_server_inbox_loaded_file_builds_compatible_package(tmp_path):
    inbox = ensure_import_inbox_dir(tmp_path / "imports" / "inbox")
    content = b"nome,email\nAna,a@x.com\n"
    (inbox / "leads.csv").write_bytes(content)

    file_name, loaded = load_import_inbox_file("leads.csv", inbox)
    package = build_import_package(file_name, loaded, SERVER_INBOX_SOURCE)

    assert package["source"] == SERVER_INBOX_SOURCE
    assert package["file_name"] == "leads.csv"
    assert package["bytes"] == content
    assert package["diagnostics"] is None
    diagnostics = build_import_diagnostics(package["file_name"], package["bytes"], [])
    assert diagnostics["success"] is True


def test_browser_upload_package_source_is_available():
    package = build_import_package("leads.csv", b"nome,email\nAna,a@x.com\n", UPLOAD_BROWSER_SOURCE)
    assert package["source"] == UPLOAD_BROWSER_SOURCE
    assert package["sha256"] == file_sha256(package["bytes"])


def test_import_inbox_gitignore_protects_real_import_files():
    gitignore = Path(".gitignore").read_text()
    assert "imports/" in gitignore
