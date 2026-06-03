from __future__ import annotations

from datetime import datetime
from typing import Any

from operia_crm.database.db import get_conn

DEFAULT_AI_PROMPT = '''Você é um assistente comercial do OperIA CRM — Empório, especializado em prospecção B2B e atendimento assistido para gestão comercial, relacionamento com clientes e rotinas internas do Empório Restaurante.

Analise os dados atuais do lead e do histórico de contatos/interações disponíveis.

Gere uma análise comercial em texto livre, útil para tomada de decisão.

Inclua, quando possível:
- resumo do potencial do lead;
- prioridade comercial em linguagem natural;
- justificativa da oportunidade;
- mensagem principal para WhatsApp;
- mensagem curta para WhatsApp;
- sugestão objetiva de próxima ação.

O operador humano sempre revisa, confirma e executa a ação.'''

PROVIDER_OPTIONS = ("Ollama", "Gemini", "Cloudflare", "Outro")
PROVIDER_TYPES = ("local", "api")

AI_SCHEMA = '''
CREATE TABLE IF NOT EXISTS ai_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    commercial_name TEXT NOT NULL,
    commercial_description TEXT NOT NULL,
    communication_tone TEXT NOT NULL,
    auto_priority INTEGER NOT NULL DEFAULT 1,
    prompt_template TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ai_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    model_name TEXT NOT NULL,
    base_url TEXT,
    provider_ref TEXT,
    active INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 99,
    last_test_at TEXT,
    last_test_status TEXT,
    last_test_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ai_model_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    test_message TEXT,
    status TEXT NOT NULL,
    result_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(model_id) REFERENCES ai_models(id)
);
CREATE TABLE IF NOT EXISTS ai_prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
'''


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _as_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _bool_int(value: bool | int) -> int:
    return 1 if bool(value) else 0


def ensure_ai_config_schema() -> None:
    with get_conn() as conn:
        conn.executescript(AI_SCHEMA)
        conn.execute(
            """
            INSERT OR IGNORE INTO ai_settings (
                id, commercial_name, commercial_description, communication_tone, auto_priority, prompt_template
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "OperIA CRM — Empório",
                "CRM comercial assistido por IA para gestão comercial, relacionamento com clientes e rotinas internas do Empório Restaurante.",
                "Profissional, direto e comercial, com abordagem consultiva e sem linguagem robótica.",
                1,
                DEFAULT_AI_PROMPT,
            ),
        )
        defaults = [
            (1, "Ollama", "local", "qwen2.5:1.5b", "http://localhost:11434", "", 1, 1),
            (2, "Gemini", "api", "gemini-1.5-flash", "", "", 0, 2),
            (3, "Cloudflare", "api", "@cf/meta/llama-3.1-8b-instruct", "", "", 0, 3),
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO ai_models (
                id, provider_name, provider_type, model_name, base_url, provider_ref, active, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            defaults,
        )


def validate_provider_type(provider_type: str) -> str:
    provider_type = _clean(provider_type).lower()
    if provider_type not in PROVIDER_TYPES:
        raise ValueError("Tipo de provedor inválido")
    return provider_type


def get_ai_settings() -> dict[str, Any]:
    ensure_ai_config_schema()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM ai_settings WHERE id = 1").fetchone()
        return _as_dict(row)


def update_ai_settings(
    commercial_name: str,
    commercial_description: str,
    communication_tone: str,
    auto_priority: bool,
    prompt_template: str,
) -> None:
    ensure_ai_config_schema()
    commercial_name = _clean(commercial_name) or "OperIA CRM — Empório"
    commercial_description = _clean(commercial_description)
    communication_tone = _clean(communication_tone) or "Profissional, direto e comercial."
    prompt_template = _clean(prompt_template) or DEFAULT_AI_PROMPT
    with get_conn() as conn:
        previous = conn.execute("SELECT prompt_template FROM ai_settings WHERE id = 1").fetchone()
        conn.execute(
            """
            UPDATE ai_settings
               SET commercial_name = ?, commercial_description = ?, communication_tone = ?,
                   auto_priority = ?, prompt_template = ?, updated_at = ?
             WHERE id = 1
            """,
            (commercial_name, commercial_description, communication_tone, _bool_int(auto_priority), prompt_template, _now()),
        )
        if previous is None or previous["prompt_template"] != prompt_template:
            conn.execute(
                "INSERT INTO ai_prompt_versions (origin, prompt_template) VALUES (?, ?)",
                ("manual", prompt_template),
            )


def restore_default_ai_prompt() -> None:
    ensure_ai_config_schema()
    with get_conn() as conn:
        conn.execute(
            "UPDATE ai_settings SET prompt_template = ?, updated_at = ? WHERE id = 1",
            (DEFAULT_AI_PROMPT, _now()),
        )
        conn.execute(
            "INSERT INTO ai_prompt_versions (origin, prompt_template) VALUES (?, ?)",
            ("restore_default", DEFAULT_AI_PROMPT),
        )


def list_ai_models(active: bool | None = None) -> list[dict[str, Any]]:
    ensure_ai_config_schema()
    sql = "SELECT * FROM ai_models"
    params: tuple[Any, ...] = ()
    if active is not None:
        sql += " WHERE active = ?"
        params = (_bool_int(active),)
    sql += " ORDER BY priority ASC, id ASC"
    with get_conn() as conn:
        return [_as_dict(row) for row in conn.execute(sql, params).fetchall()]


def get_ai_model(model_id: int) -> dict[str, Any] | None:
    ensure_ai_config_schema()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,)).fetchone()
        return _as_dict(row) if row else None


def _next_priority(conn) -> int:
    row = conn.execute("SELECT COALESCE(MAX(priority), 0) AS max_priority FROM ai_models").fetchone()
    return int(row["max_priority"] or 0) + 1


def create_ai_model(
    provider_name: str,
    provider_type: str,
    model_name: str,
    base_url: str = "",
    provider_ref: str = "",
    active: bool = True,
    priority: int | None = None,
) -> int:
    ensure_ai_config_schema()
    provider_name = _clean(provider_name) or "Outro"
    provider_type = validate_provider_type(provider_type)
    model_name = _clean(model_name)
    if not model_name:
        raise ValueError("Nome do modelo é obrigatório")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO ai_models (
                provider_name, provider_type, model_name, base_url, provider_ref, active, priority, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (provider_name, provider_type, model_name, _clean(base_url), _clean(provider_ref), _bool_int(active), int(priority or _next_priority(conn)), _now()),
        )
        return int(cur.lastrowid)


def update_ai_model(
    model_id: int,
    provider_name: str,
    provider_type: str,
    model_name: str,
    base_url: str = "",
    provider_ref: str = "",
    active: bool = True,
    priority: int = 99,
) -> None:
    ensure_ai_config_schema()
    provider_name = _clean(provider_name) or "Outro"
    provider_type = validate_provider_type(provider_type)
    model_name = _clean(model_name)
    if not model_name:
        raise ValueError("Nome do modelo é obrigatório")
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE ai_models
               SET provider_name = ?, provider_type = ?, model_name = ?, base_url = ?, provider_ref = ?,
                   active = ?, priority = ?, updated_at = ?
             WHERE id = ?
            """,
            (provider_name, provider_type, model_name, _clean(base_url), _clean(provider_ref), _bool_int(active), int(priority), _now(), int(model_id)),
        )


def set_ai_model_active(model_id: int, active: bool) -> None:
    ensure_ai_config_schema()
    with get_conn() as conn:
        conn.execute(
            "UPDATE ai_models SET active = ?, updated_at = ? WHERE id = ?",
            (_bool_int(active), _now(), int(model_id)),
        )


def save_ai_model_priorities(priority_by_model_id: dict[int, int]) -> None:
    ensure_ai_config_schema()
    with get_conn() as conn:
        for model_id, priority in priority_by_model_id.items():
            conn.execute(
                "UPDATE ai_models SET priority = ?, updated_at = ? WHERE id = ?",
                (int(priority), _now(), int(model_id)),
            )


def mask_secret_reference(provider_ref: str | None) -> str:
    provider_ref = _clean(provider_ref)
    if not provider_ref:
        return "-"
    return f"{provider_ref} (referenciado)"


def run_ai_model_config_test(model_id: int, test_message: str = "") -> dict[str, str]:
    model = get_ai_model(model_id)
    if not model:
        raise ValueError("Modelo não encontrado")
    provider_type = model["provider_type"]
    base_url = _clean(model.get("base_url"))
    provider_ref = _clean(model.get("provider_ref"))
    model_name = _clean(model.get("model_name"))
    if not model_name:
        status = "Falha"
        result_message = "Nome do modelo não configurado."
    elif provider_type == "local":
        if base_url.startswith("http://") or base_url.startswith("https://"):
            status = "Sucesso"
            result_message = "Configuração local validada. Inferência real fica para a fase 2."
        else:
            status = "Falha"
            result_message = "Base URL local inválida. Use http://host:porta."
    elif provider_type == "api":
        if provider_ref:
            status = "Sucesso"
            result_message = "Referência externa cadastrada. Chamada real do provider fica para a fase 2."
        else:
            status = "Pendente"
            result_message = "Informe a referência externa antes da chamada real."
    else:
        status = "Falha"
        result_message = "Tipo de provedor inválido."
    timestamp = _now()
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE ai_models
               SET last_test_at = ?, last_test_status = ?, last_test_message = ?, updated_at = ?
             WHERE id = ?
            """,
            (timestamp, status, result_message, timestamp, int(model_id)),
        )
        conn.execute(
            """
            INSERT INTO ai_model_tests (model_id, test_message, status, result_message)
            VALUES (?, ?, ?, ?)
            """,
            (int(model_id), _clean(test_message), status, result_message),
        )
    return {"status": status, "message": result_message, "tested_at": timestamp}
