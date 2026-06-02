from operia_crm.config.settings import settings


def suggest_message(name: str, context: str) -> str:
    try:
        from operia_crm.services.ai_config import get_ai_settings

        ai_settings = get_ai_settings()
        commercial_name = ai_settings.get("commercial_name") or "OperIA CRM — Empório"
    except Exception:
        commercial_name = "OperIA CRM — Empório"

    if settings.gemini_api_key:
        return f'[Gemini opcional configurado] Olá {name}, {context}. Podemos falar hoje? — {commercial_name}'
    return f'Olá {name}, {context}. Podemos falar hoje? — {commercial_name}'
