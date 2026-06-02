import pytest

from operia_crm.config.settings import settings as app_settings
from operia_crm.database.db import init_db
from operia_crm.services.ai_config import (
    DEFAULT_AI_PROMPT,
    create_ai_model,
    get_ai_settings,
    list_ai_models,
    restore_default_ai_prompt,
    run_ai_model_config_test,
    set_ai_model_active,
    update_ai_settings,
)


@pytest.fixture()
def isolated_env(tmp_path):
    original_db = app_settings.db_path
    original_attachments = app_settings.attachments_dir
    original_backups = app_settings.backups_dir
    object.__setattr__(app_settings, "db_path", tmp_path / "test.db")
    object.__setattr__(app_settings, "attachments_dir", tmp_path / "attachments")
    object.__setattr__(app_settings, "backups_dir", tmp_path / "backups")
    init_db()
    try:
        yield tmp_path
    finally:
        object.__setattr__(app_settings, "db_path", original_db)
        object.__setattr__(app_settings, "attachments_dir", original_attachments)
        object.__setattr__(app_settings, "backups_dir", original_backups)


def test_ai_defaults_seeded(isolated_env):
    settings = get_ai_settings()
    models = list_ai_models()

    assert settings["commercial_name"] == "OperIA CRM — Empório"
    assert DEFAULT_AI_PROMPT in settings["prompt_template"]
    assert len(models) >= 3
    assert models[0]["provider_name"] == "Ollama"


def test_ai_settings_update_and_restore(isolated_env):
    update_ai_settings(
        commercial_name="Empresa Teste",
        commercial_description="Descrição comercial teste",
        communication_tone="Direto e consultivo",
        auto_priority=False,
        prompt_template="Prompt customizado",
    )

    settings = get_ai_settings()
    assert settings["commercial_name"] == "Empresa Teste"
    assert settings["auto_priority"] == 0
    assert settings["prompt_template"] == "Prompt customizado"

    restore_default_ai_prompt()
    restored = get_ai_settings()
    assert restored["prompt_template"] == DEFAULT_AI_PROMPT


def test_ai_model_crud_activation_and_config_test(isolated_env):
    model_id = create_ai_model(
        provider_name="Ollama",
        provider_type="local",
        model_name="qwen2.5:1.5b",
        base_url="http://localhost:11434",
        active=True,
        priority=4,
    )

    active_models = list_ai_models(active=True)
    assert any(model["id"] == model_id for model in active_models)

    result = run_ai_model_config_test(model_id, "Teste rápido")
    assert result["status"] == "Sucesso"

    set_ai_model_active(model_id, False)
    inactive_models = list_ai_models(active=False)
    assert any(model["id"] == model_id for model in inactive_models)
