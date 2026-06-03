from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Any

from operia_crm.database.db import get_conn
from operia_crm.services.core import list_leads, register_interaction

MAX_WORK_ACTIONS = 5
ACTION_MARKER_PREFIX = "[operia-work-action:"
FUNNEL_STAGES = [
    "Novos contatos",
    "Contato iniciado",
    "Proposta enviada",
    "Em negociação",
    "Fechados",
]

CLOSED_MARKERS = ("ganho", "ganha", "fechado", "fechada", "perdido", "perdida", "cancelado", "cancelada")
NEGOTIATION_MARKERS = ("negociação", "negociacao")
PROPOSAL_MARKERS = ("proposta",)
NEW_MARKERS = ("novo",)
TECHNICAL_TERMS = (
    "provider",
    "model",
    "fallback",
    "sqlite",
    "database",
    "debug",
    "log",
    "path",
    "token",
    "api error",
    "stacktrace",
)


def _to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    return dict(row)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _normalize_signature(value: Any) -> str:
    text = _lower(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _has_contact(lead: dict[str, Any]) -> bool:
    return bool(_text(lead.get("phone")) or _text(lead.get("whatsapp")) or _text(lead.get("email")))


def _has_required_context(lead: dict[str, Any]) -> bool:
    return bool(_has_contact(lead) and _text(lead.get("origin")) and _text(lead.get("status")))


def _is_open_proposal(status: Any) -> bool:
    return not _has_any(_lower(status), CLOSED_MARKERS)


def _open_proposals_by_lead(proposals: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for proposal in proposals:
        if not _is_open_proposal(proposal.get("status")):
            continue
        lead_id = _int(proposal.get("lead_id"))
        if lead_id:
            grouped.setdefault(lead_id, []).append(proposal)
    return grouped


def _pending_interactions_by_lead(interactions: list[dict[str, Any]]) -> dict[int, int]:
    grouped: dict[int, int] = {}
    for interaction in interactions:
        if _int(interaction.get("pending")) != 1:
            continue
        lead_id = _int(interaction.get("lead_id"))
        if lead_id:
            grouped[lead_id] = grouped.get(lead_id, 0) + 1
    return grouped


def _duplicate_groups(leads: list[dict[str, Any]]) -> dict[int, str]:
    strong_seen: dict[str, int] = {}
    probable_seen: dict[str, int] = {}
    duplicate_by_id: dict[int, str] = {}

    for lead in sorted(leads, key=lambda item: _int(item.get("id"))):
        lead_id = _int(lead.get("id"))
        keys = [
            re.sub(r"\D", "", _text(lead.get("phone"))),
            re.sub(r"\D", "", _text(lead.get("whatsapp"))),
            _lower(lead.get("email")),
        ]
        probable = f"{_normalize_signature(lead.get('name'))}|{_normalize_signature(lead.get('city'))}"

        matched = False
        for key in [item for item in keys if item]:
            if key in strong_seen:
                duplicate_by_id[lead_id] = "Duplicidade provável: mesmo canal de contato."
                duplicate_by_id.setdefault(strong_seen[key], "Duplicidade provável: mesmo canal de contato.")
                matched = True
            else:
                strong_seen[key] = lead_id

        if probable.strip("|"):
            if probable in probable_seen:
                duplicate_by_id[lead_id] = "Duplicidade possível: mesmo nome e cidade."
                duplicate_by_id.setdefault(probable_seen[probable], "Duplicidade possível: mesmo nome e cidade.")
            else:
                probable_seen[probable] = lead_id

        if matched:
            continue

    return duplicate_by_id


def _lead_stage(status: str, has_open_proposal: bool, is_closed: bool, is_negotiation: bool, has_proposal_status: bool) -> str:
    if is_closed:
        return "Fechados"
    if is_negotiation:
        return "Em negociação"
    if has_open_proposal or has_proposal_status:
        return "Proposta enviada"
    if _has_any(status, NEW_MARKERS):
        return "Novos contatos"
    return "Contato iniciado"


def _build_lead_facts(
    leads: list[dict[str, Any]],
    *,
    open_proposals: dict[int, list[dict[str, Any]]],
    pending_by_lead: dict[int, int],
    duplicate_by_id: dict[int, str],
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for lead in leads:
        lead_id = _int(lead.get("id"))
        status = _lower(lead.get("status"))
        score = _int(lead.get("score"))
        is_closed = _has_any(status, CLOSED_MARKERS)
        is_negotiation = _has_any(status, NEGOTIATION_MARKERS)
        has_proposal_status = _has_any(status, PROPOSAL_MARKERS)
        has_open_proposal = bool(not is_closed and (lead_id in open_proposals or has_proposal_status))
        pending_count = pending_by_lead.get(lead_id, 0)
        next_followup = lead.get("next_followup")
        stage = _lead_stage(status, has_open_proposal, is_closed, is_negotiation, has_proposal_status)
        is_high_opportunity = bool(not is_closed and (has_open_proposal or is_negotiation or score >= 70))
        has_next_action = bool(has_open_proposal or pending_count > 0 or next_followup)
        duplicate_risk = duplicate_by_id.get(lead_id, "")

        fact = dict(lead)
        fact.update(
            {
                "_lead_id": lead_id,
                "_score": score,
                "_stage": stage,
                "_has_open_proposal": has_open_proposal,
                "_open_proposals_count": len(open_proposals.get(lead_id, [])),
                "_pending_interactions_count": pending_count,
                "_has_next_followup": bool(next_followup),
                "_has_next_action": has_next_action,
                "_needs_return": bool(not is_closed and has_next_action),
                "_is_high_opportunity": is_high_opportunity,
                "_is_closed": is_closed,
                "_is_negotiation": is_negotiation,
                "_has_proposal_status": has_proposal_status,
                "_is_new": stage == "Novos contatos",
                "_has_contact": _has_contact(lead),
                "_is_incomplete": not _has_required_context(lead),
                "_duplicate_risk": duplicate_risk,
            }
        )
        facts.append(fact)
    return facts


def _action_priority(fact: dict[str, Any]) -> tuple[int, int, int]:
    if fact.get("_is_closed"):
        priority = 99
    elif fact.get("_duplicate_risk"):
        priority = 5
    elif fact.get("_has_open_proposal"):
        priority = 10
    elif fact.get("_is_negotiation"):
        priority = 20
    elif _int(fact.get("_pending_interactions_count")) > 0:
        priority = 30
    elif fact.get("_has_next_followup"):
        priority = 40
    elif fact.get("_is_high_opportunity"):
        priority = 50
    elif fact.get("_is_new"):
        priority = 60
    elif fact.get("_is_incomplete"):
        priority = 70
    else:
        priority = 99
    return (priority, -_int(fact.get("_score")), _int(fact.get("_lead_id")))


def _idempotency_key(action: dict[str, Any], reference_date: str) -> str:
    lead_id = _int(action.get("lead_id"))
    action_type = _normalize_signature(action.get("type"))
    status_context = _normalize_signature(action.get("status_context") or action.get("reason"))
    if lead_id:
        base = f"{lead_id}|{action_type}|{status_context}|{reference_date}"
    else:
        base = "|".join(
            [
                _normalize_signature(action.get("lead_name")),
                _normalize_signature(action.get("city")),
                action_type,
                reference_date,
            ]
        )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:20]


def _weight_for_fact(fact: dict[str, Any]) -> str:
    if fact.get("_duplicate_risk") or fact.get("_has_open_proposal") or fact.get("_is_negotiation"):
        return "Alto"
    if fact.get("_pending_interactions_count") or fact.get("_has_next_followup") or fact.get("_is_high_opportunity"):
        return "Médio"
    return "Baixo"


def _action_for_fact(fact: dict[str, Any], reference_date: str) -> dict[str, Any]:
    action_type = "registrar_sugestao_proxima_acao"
    title = "Registrar sugestão de próxima ação"
    reason = "Prioridade comercial identificada na carteira."
    impact = "Mantém a carteira ativa e reduz perda de timing comercial."
    prepared_content = "Registrar próxima ação comercial para revisão manual."
    state = "aguardando liberação"
    suggested_message = ""

    if fact.get("_duplicate_risk"):
        action_type = "bloquear_acao_duplicada"
        title = "Bloquear ação duplicada"
        reason = fact.get("_duplicate_risk") or "Contato com risco de duplicidade."
        impact = "Evita registros repetidos e protege a qualidade da carteira."
        prepared_content = "Revisar possível duplicidade antes de executar nova ação comercial."
        state = "bloqueada por duplicidade"
    elif fact.get("_has_open_proposal"):
        action_type = "criar_retorno_pendente"
        title = "Criar retorno pendente"
        reason = "Proposta em aberto aguardando retorno."
        impact = "Aumenta a chance de conversão antes da proposta esfriar."
        prepared_content = "Retornar contato sobre proposta em aberto."
        suggested_message = f"Olá, {fact.get('name') or 'tudo bem'}? Passando para saber se ficou alguma dúvida sobre a proposta."
    elif fact.get("_is_negotiation"):
        action_type = "registrar_interacao_interna"
        title = "Registrar interação interna"
        reason = "Contato em negociação aguardando condução."
        impact = "Ajuda a avançar uma negociação já qualificada."
        prepared_content = "Registrar próximo passo da negociação."
        suggested_message = f"Olá, {fact.get('name') or 'tudo bem'}? Podemos alinhar o próximo passo da negociação?"
    elif _int(fact.get("_pending_interactions_count")) > 0:
        action_type = "registrar_alerta_comercial_interno"
        title = "Registrar alerta comercial interno"
        reason = "Interação pendente registrada."
        impact = "Evita que pendências abertas bloqueiem o avanço comercial."
        prepared_content = "Revisar interação pendente e registrar encaminhamento."
    elif fact.get("_has_next_followup"):
        action_type = "criar_retorno_pendente"
        title = "Criar retorno pendente"
        reason = "Retorno agendado no CRM."
        impact = "Cumpre o combinado com o contato e preserva cadência."
        prepared_content = "Registrar retorno comercial agendado."
        suggested_message = f"Olá, {fact.get('name') or 'tudo bem'}? Estou retomando nosso contato conforme combinado."
    elif fact.get("_is_high_opportunity"):
        action_type = "registrar_sugestao_proxima_acao"
        reason = "Oportunidade em alta sem próxima ação."
        impact = "Transforma potencial comercial em próximo passo claro."
        prepared_content = "Definir próxima ação comercial para oportunidade em alta."
    elif fact.get("_is_new"):
        action_type = "preparar_mensagem_comercial_revisao"
        title = "Preparar mensagem comercial para revisão"
        reason = "Contato novo aguardando qualificação."
        impact = "Acelera a qualificação inicial e reduz contatos parados."
        prepared_content = "Preparar primeiro contato e próximos passos para revisão."
        suggested_message = f"Olá, {fact.get('name') or 'tudo bem'}? Recebi seu contato e queria entender melhor sua necessidade."
    elif fact.get("_is_incomplete"):
        action_type = "cadastro_incompleto"
        title = "Sinalizar contato incompleto"
        reason = "Cadastro incompleto limita a próxima ação."
        impact = "Melhora a qualidade da carteira e evita tentativas sem canal válido."
        prepared_content = "Revisar dados essenciais do contato antes do próximo avanço."

    action = {
        "type": action_type,
        "lead_id": fact.get("_lead_id"),
        "lead_name": fact.get("name") or "Contato",
        "city": fact.get("city") or "",
        "weight": _weight_for_fact(fact),
        "reason": reason,
        "impact": impact,
        "prepared_content": prepared_content,
        "state": state,
        "status_context": fact.get("_stage"),
        "title": title,
        "content": prepared_content,
        "suggested_message": suggested_message,
        "priority": _action_priority(fact)[0],
    }
    action["idempotency_key"] = _idempotency_key(action, reference_date)
    action["fingerprint"] = action["idempotency_key"]
    return action


def deduplicate_work_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for action in actions or []:
        key = str(action.get("idempotency_key") or action.get("fingerprint") or "").strip()
        if not key:
            key = _idempotency_key(action, date.today().isoformat())
            action = {**action, "idempotency_key": key, "fingerprint": key}
        if key in seen:
            continue
        seen.add(key)
        unique.append(action)
    return unique


def _build_action_candidates(facts: list[dict[str, Any]], reference_date: str) -> list[dict[str, Any]]:
    eligible = [fact for fact in facts if _action_priority(fact)[0] < 99]
    return deduplicate_work_actions([_action_for_fact(fact, reference_date) for fact in sorted(eligible, key=_action_priority)])


def _select_prepared_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique_actions = deduplicate_work_actions(actions)
    productive = [action for action in unique_actions if action.get("state") != "bloqueada por duplicidade"]
    blocked = [action for action in unique_actions if action.get("state") == "bloqueada por duplicidade"]

    if not productive:
        return blocked[:MAX_WORK_ACTIONS]

    productive_limit = MAX_WORK_ACTIONS - 1 if blocked else MAX_WORK_ACTIONS
    selected = productive[:productive_limit]
    remaining_slots = MAX_WORK_ACTIONS - len(selected)
    if remaining_slots > 0:
        selected.extend(blocked[: min(2, remaining_slots)])
    return selected[:MAX_WORK_ACTIONS]


def build_operational_snapshot() -> dict[str, Any]:
    leads = [_to_dict(row) for row in list_leads()]
    lead_ids = [_int(lead.get("id")) for lead in leads if lead.get("id") is not None]
    proposals: list[dict[str, Any]] = []
    interactions: list[dict[str, Any]] = []

    with get_conn() as conn:
        if lead_ids:
            placeholders = ",".join(["?"] * len(lead_ids))
            proposals = [_to_dict(row) for row in conn.execute(f"SELECT * FROM proposals WHERE lead_id IN ({placeholders})", tuple(lead_ids)).fetchall()]
            interactions = [_to_dict(row) for row in conn.execute(f"SELECT * FROM interactions WHERE lead_id IN ({placeholders})", tuple(lead_ids)).fetchall()]

    open_proposals = _open_proposals_by_lead(proposals)
    pending_by_lead = _pending_interactions_by_lead(interactions)
    duplicate_by_id = _duplicate_groups(leads)
    lead_facts = _build_lead_facts(
        leads,
        open_proposals=open_proposals,
        pending_by_lead=pending_by_lead,
        duplicate_by_id=duplicate_by_id,
    )
    funnel = {stage: 0 for stage in FUNNEL_STAGES}
    for fact in lead_facts:
        funnel[fact["_stage"]] += 1

    action_candidates = _build_action_candidates(lead_facts, date.today().isoformat())
    opportunities_high = sum(1 for fact in lead_facts if fact.get("_is_high_opportunity"))
    returns_todo = sum(1 for fact in lead_facts if fact.get("_needs_return"))
    contacts_without_next_action = sum(1 for fact in lead_facts if not fact.get("_is_closed") and not fact.get("_has_next_action"))

    return {
        "total_contatos": len(leads),
        "oportunidades_em_alta": opportunities_high,
        "retornos_a_fazer": returns_todo,
        "propostas_em_aberto": sum(1 for fact in lead_facts if fact.get("_has_open_proposal")),
        "contatos_novos": funnel["Novos contatos"],
        "contatos_proposta_enviada": funnel["Proposta enviada"],
        "contatos_em_negociacao": funnel["Em negociação"],
        "contatos_fechados": funnel["Fechados"],
        "contatos_sem_proxima_acao": contacts_without_next_action,
        "contatos_incompletos": sum(1 for fact in lead_facts if fact.get("_is_incomplete")),
        "contatos_com_risco_duplicidade": len(duplicate_by_id),
        "interacoes_pendentes": [item for item in interactions if _int(item.get("pending")) == 1],
        "propostas_abertas": [proposal for group in open_proposals.values() for proposal in group],
        "lead_facts": lead_facts,
        "action_candidates": action_candidates,
        "funnel": funnel,
        "evidence": [
            "Oportunidades em alta: contatos em negociação, com proposta em aberto ou pontuação alta.",
            "Retornos: contatos com proposta aberta, interação pendente ou retorno agendado.",
            "Propostas em aberto: propostas ainda não marcadas como ganhas, perdidas, fechadas ou canceladas.",
            "Duplicidade: mesmo telefone, WhatsApp, e-mail ou combinação de nome e cidade.",
        ],
    }


def _package_signature(actions: list[dict[str, Any]]) -> str:
    keys = sorted(str(action.get("idempotency_key") or "") for action in actions if action.get("idempotency_key"))
    raw = "|".join(keys) or "empty-operational-package"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _main_action(snapshot: dict[str, Any]) -> str:
    if _int(snapshot.get("total_contatos")) == 0:
        return "Cadastre ou importe contatos para iniciar a leitura da carteira."
    if _int(snapshot.get("contatos_com_risco_duplicidade")) > 0:
        return "Revisar duplicidades antes de liberar novas ações comerciais."
    if _int(snapshot.get("propostas_em_aberto")) > 0:
        return "Retornar primeiro as propostas em aberto antes de iniciar novos contatos."
    if _int(snapshot.get("retornos_a_fazer")) > 0:
        return "Executar retornos pendentes antes de prospectar novos contatos."
    if _int(snapshot.get("oportunidades_em_alta")) > 0:
        return "Definir próxima ação para as oportunidades em alta."
    return "Revisar a carteira e liberar apenas ações internas necessárias."


def _sanitize_package(package: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(package, ensure_ascii=False).lower()
    if not any(term in text for term in TECHNICAL_TERMS):
        return package
    package = dict(package)
    package["assistant_text"] = "Análise automática indisponível no momento. Exibindo leitura local da carteira."
    return package


def prepare_ai_work_package(snapshot: dict[str, Any]) -> dict[str, Any]:
    actions = deduplicate_work_actions(list(snapshot.get("action_candidates") or []))
    prepared_actions = _select_prepared_actions(actions)
    productive_actions = [action for action in prepared_actions if action.get("state") != "bloqueada por duplicidade"]
    blocked_actions = [action for action in prepared_actions if action.get("state") == "bloqueada por duplicidade"]
    blocked = sum(1 for action in prepared_actions if action.get("state") == "bloqueada por duplicidade")
    counts = {
        "acoes_preparadas": len(prepared_actions),
        "retornos_pendentes": sum(1 for action in prepared_actions if action.get("type") == "criar_retorno_pendente"),
        "mensagens_para_revisao": sum(1 for action in prepared_actions if action.get("suggested_message")),
        "alertas_internos": sum(1 for action in prepared_actions if "alerta" in str(action.get("type"))),
        "bloqueadas_por_duplicidade": blocked,
        "acoes_identificadas": len(actions),
        "acoes_exibidas": len(prepared_actions),
    }
    package = {
        "main_action": _main_action(snapshot),
        "assistant_text": "A carteira foi analisada localmente. A IA preparou ações internas para revisão e visto do operador.",
        "alerts": [
            alert
            for alert in [
                f"{snapshot.get('contatos_com_risco_duplicidade')} contatos com risco de duplicidade." if _int(snapshot.get("contatos_com_risco_duplicidade")) else "",
                f"{snapshot.get('propostas_em_aberto')} propostas em aberto precisam de retorno." if _int(snapshot.get("propostas_em_aberto")) else "",
                f"{snapshot.get('contatos_incompletos')} contatos incompletos precisam de revisão." if _int(snapshot.get("contatos_incompletos")) else "",
            ]
            if alert
        ][:3],
        "prepared_actions": prepared_actions,
        "productive_actions": productive_actions,
        "blocked_actions": blocked_actions,
        "day_queue": productive_actions or prepared_actions,
        "package_signature": _package_signature(prepared_actions),
        "counts": counts,
        "funnel": snapshot.get("funnel") or {stage: 0 for stage in FUNNEL_STAGES},
        "evidence": snapshot.get("evidence") or [],
    }
    return _sanitize_package(package)


def apply_approved_work_package(package: dict[str, Any] | list[dict[str, Any]], approved: bool = False) -> int:
    if not approved:
        return 0
    actions = package if isinstance(package, list) else package.get("prepared_actions") or []
    created = 0
    for action in deduplicate_work_actions(list(actions)):
        if action.get("state") == "bloqueada por duplicidade":
            continue
        lead_id = _int(action.get("lead_id"))
        if not lead_id:
            continue
        key = str(action.get("idempotency_key") or action.get("fingerprint") or "").strip()
        marker = f"{ACTION_MARKER_PREFIX}{key}]"
        with get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM interactions WHERE lead_id = ? AND summary LIKE ? LIMIT 1",
                (lead_id, f"%{marker}%"),
            ).fetchone()
        if existing:
            continue
        summary = (
            f"{marker} {action.get('title') or 'Ação preparada pela IA'}: "
            f"{action.get('prepared_content') or action.get('content') or ''} "
            f"Motivo: {action.get('reason') or 'Prioridade comercial.'} "
            f"Impacto: {action.get('impact') or 'Apoia a execução comercial.'} "
            "(Preparado pela IA e aprovado pelo operador)"
        )
        register_interaction(lead_id, "Ação preparada pela IA", summary, "manual")
        action["state"] = "registrada"
        created += 1
    return created


def build_leads_operational_view() -> list[dict[str, Any]]:
    snapshot = build_operational_snapshot()
    rows: list[dict[str, Any]] = []
    for fact in sorted(snapshot.get("lead_facts") or [], key=_action_priority):
        next_action = _action_for_fact(fact, date.today().isoformat())
        rows.append(
            {
                "Contato": fact.get("name") or "Contato",
                "Cidade/UF": fact.get("city") or "-",
                "Segmento": fact.get("segment") or "-",
                "Potencial IA": "Alto" if fact.get("_is_high_opportunity") else ("Médio" if fact.get("_is_new") else "Baixo"),
                "Status operacional": fact.get("_stage") or "Contato iniciado",
                "Próxima ação sugerida": next_action.get("title"),
                "Risco de duplicidade": fact.get("_duplicate_risk") or "Sem alerta",
                "_lead_id": fact.get("_lead_id"),
                "_action": next_action,
            }
        )
    return rows
