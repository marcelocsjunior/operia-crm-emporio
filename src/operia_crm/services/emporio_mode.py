from __future__ import annotations

from datetime import date, datetime
from typing import Any

OPPORTUNITY_TYPES = [
    "Reserva",
    "Evento",
    "Encomenda",
    "Marmita / refeição recorrente",
    "Cliente corporativo",
    "Parceria",
    "Reativação",
    "Outro",
]

EMPORIO_STATUSES = [
    "Novo contato",
    "Qualificar demanda",
    "Proposta/cardápio enviado",
    "Aguardando retorno",
    "Confirmado / fechado",
    "Perdido",
    "Reativar futuramente",
]

EMPORIO_IMPORT_ALIASES = {
    "tipo_oportunidade": "opportunity_type",
    "opportunity_type": "opportunity_type",
    "data_evento_ou_entrega": "event_or_delivery_date",
    "event_or_delivery_date": "event_or_delivery_date",
    "valor_estimado": "estimated_value",
    "estimated_value": "estimated_value",
    "quantidade_pessoas": "people_count",
    "people_count": "people_count",
    "canal_origem": "source_channel",
    "source_channel": "source_channel",
    "status_emporio": "emporio_status",
    "emporio_status": "emporio_status",
    "proxima_acao": "next_action",
    "next_action": "next_action",
    "observacao_operacional": "operational_notes",
    "operational_notes": "operational_notes",
}

EMPORIO_DISPLAY_COLUMNS = {
    "opportunity_type": "Tipo de oportunidade",
    "event_or_delivery_date": "Data do evento/entrega/reserva",
    "estimated_value": "Valor estimado",
    "people_count": "Quantidade de pessoas",
    "source_channel": "Canal de origem",
    "emporio_status": "Status Empório",
    "next_action": "Próxima ação",
    "operational_notes": "Observação operacional",
}

HIGH_VALUE_THRESHOLD = 1000.0
HIGH_PEOPLE_THRESHOLD = 20


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "<na>"} else text


def _clean_number(value: Any) -> float:
    text = _clean(value)
    if not text:
        return 0.0
    normalized = text.replace("R$", "").replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return max(0.0, float(normalized))
    except ValueError:
        return 0.0


def _clean_int(value: Any) -> int:
    try:
        return max(0, int(_clean_number(value)))
    except (TypeError, ValueError):
        return 0


def parse_emporio_date(value: Any) -> date | None:
    text = _clean(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def normalize_opportunity_type(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    by_key = {item.lower(): item for item in OPPORTUNITY_TYPES}
    return by_key.get(text.lower(), "Outro")


def normalize_emporio_status(value: Any) -> str:
    text = _clean(value)
    if not text:
        return "Novo contato"
    by_key = {item.lower(): item for item in EMPORIO_STATUSES}
    return by_key.get(text.lower(), "Novo contato")


def parse_emporio_import_fields(row: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for raw_key, value in row.items():
        mapped = EMPORIO_IMPORT_ALIASES.get(str(raw_key).strip().lower())
        if not mapped:
            continue
        if mapped == "opportunity_type":
            parsed[mapped] = normalize_opportunity_type(value)
        elif mapped == "emporio_status":
            parsed[mapped] = normalize_emporio_status(value)
        elif mapped == "estimated_value":
            parsed[mapped] = _clean_number(value)
        elif mapped == "people_count":
            parsed[mapped] = _clean_int(value)
        elif mapped == "event_or_delivery_date":
            parsed[mapped] = parse_emporio_date(value).isoformat() if parse_emporio_date(value) else None
        else:
            parsed[mapped] = _clean(value) or None
    return parsed


def calculate_emporio_priority(lead: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    status = normalize_emporio_status(lead.get("emporio_status") or lead.get("status"))
    opportunity_type = normalize_opportunity_type(lead.get("opportunity_type"))
    event_date = parse_emporio_date(lead.get("event_or_delivery_date"))
    estimated_value = _clean_number(lead.get("estimated_value"))
    people_count = _clean_int(lead.get("people_count"))
    has_next_action = bool(_clean(lead.get("next_action")) or _clean(lead.get("next_followup")))
    has_contact = bool(_clean(lead.get("phone")) or _clean(lead.get("whatsapp")) or _clean(lead.get("email")))

    score = 20
    reasons: list[str] = []

    if event_date:
        days = (event_date - today).days
        if 0 <= days <= 7:
            score += 45
            reasons.append("evento/entrega nos próximos 7 dias")
        elif 8 <= days <= 14:
            score += 25
            reasons.append("data operacional próxima")
        elif days < 0:
            score += 10
            reasons.append("data operacional vencida")

    if status in {"Proposta/cardápio enviado", "Aguardando retorno"}:
        score += 30
        reasons.append("proposta/cardápio aguardando retorno")
    elif status == "Qualificar demanda":
        score += 15
        reasons.append("demanda precisa de qualificação")
    elif status == "Reativar futuramente":
        score += 10
        reasons.append("contato marcado para reativação")

    if opportunity_type in {"Cliente corporativo", "Marmita / refeição recorrente"}:
        score += 25
        reasons.append("oportunidade corporativa ou recorrente")
    elif opportunity_type in {"Evento", "Encomenda", "Parceria"}:
        score += 15
        reasons.append("tipo de oportunidade com potencial operacional")

    if estimated_value > 0:
        score += 10
        reasons.append("valor estimado informado")
    if estimated_value >= HIGH_VALUE_THRESHOLD:
        score += 10
        reasons.append("valor estimado relevante")
    if people_count >= HIGH_PEOPLE_THRESHOLD:
        score += 10
        reasons.append("quantidade de pessoas relevante")
    if not has_next_action and status not in {"Confirmado / fechado", "Perdido"}:
        score += 15
        reasons.append("sem próxima ação definida")
    if not has_contact:
        reasons.append("cadastro sem canal público válido")

    closed = status in {"Confirmado / fechado", "Perdido"}
    if closed:
        score = min(score, 35)

    if score >= 75:
        priority = "Alta"
    elif score >= 45:
        priority = "Média"
    else:
        priority = "Baixa"

    if closed:
        temperature = "Frio"
    elif score >= 75:
        temperature = "Quente"
    elif score >= 45:
        temperature = "Morno"
    else:
        temperature = "Frio"

    return {
        "score": max(0, min(100, score)),
        "priority": priority,
        "temperature": temperature,
        "reasons": reasons or ["revisar oportunidade"],
        "days_until_event": (event_date - today).days if event_date else None,
        "status": status,
        "opportunity_type": opportunity_type,
        "estimated_value": estimated_value,
        "people_count": people_count,
        "has_contact": has_contact,
        "has_next_action": has_next_action,
    }


def suggest_emporio_message(lead: dict[str, Any], action_context: str | None = None) -> str:
    name = _clean(lead.get("name")) or "tudo bem"
    opportunity_type = normalize_opportunity_type(lead.get("opportunity_type"))
    status = normalize_emporio_status(lead.get("emporio_status") or lead.get("status"))
    date_text = _clean(lead.get("event_or_delivery_date"))
    people_count = _clean_int(lead.get("people_count"))
    suffix = "A mensagem deve ser revisada pelo operador antes de qualquer envio."

    if action_context == "confirmacao" or status == "Confirmado / fechado":
        return f"Olá, {name}. Confirmando os detalhes da sua reserva/evento/encomenda{f' para {date_text}' if date_text else ''}. {suffix}"
    if action_context == "reativacao" or opportunity_type == "Reativação" or status == "Reativar futuramente":
        return f"Olá, {name}. Passando para retomar nosso contato e entender se o Empório pode atender você novamente. {suffix}"
    if opportunity_type == "Cliente corporativo":
        return f"Olá, {name}. Gostaria de alinhar como o Empório pode apoiar sua equipe com atendimento corporativo, eventos ou refeições recorrentes. {suffix}"
    if opportunity_type == "Parceria":
        return f"Olá, {name}. Podemos conversar sobre uma parceria comercial com o Empório e próximos passos? {suffix}"
    if opportunity_type == "Marmita / refeição recorrente":
        return f"Olá, {name}. Podemos alinhar volume, frequência e datas para refeições recorrentes do Empório{f' para {people_count} pessoas' if people_count else ''}? {suffix}"
    if status in {"Proposta/cardápio enviado", "Aguardando retorno"}:
        return f"Olá, {name}. Passando para saber se ficou alguma dúvida sobre a proposta/cardápio do Empório e qual próximo passo prefere seguir. {suffix}"
    if opportunity_type in {"Evento", "Encomenda", "Reserva"}:
        return f"Olá, {name}. Recebi sua demanda de {opportunity_type.lower()} e quero confirmar data, quantidade de pessoas e detalhes para o Empório atender bem. {suffix}"
    return f"Olá, {name}. Recebi seu contato e quero entender melhor como o Empório pode atender sua demanda. {suffix}"
