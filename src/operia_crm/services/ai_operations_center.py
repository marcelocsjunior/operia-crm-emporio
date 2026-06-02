from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from statistics import mean
from typing import Any

from operia_crm.database.db import get_conn
from operia_crm.services.core import list_leads, normalize_phone, normalize_text

DEDUP_MARKER_PREFIX = "[central-ia-dedup:"
NOT_DUP_MARKER_PREFIX = "[central-ia-not-duplicate:"
OPPORTUNITY_MARKER_PREFIX = "[central-ia-opportunity:"
NICHE_MARKER_PREFIX = "[central-ia-niche:"
MERGED_NOTE_PREFIX = "[Central IA] Registro mesclado operacionalmente ao lead"

TECH_DEPENDENCY_TERMS = (
    "sistema",
    "backup",
    "rede",
    "servidor",
    "internet",
    "wifi",
    "wi-fi",
    "computador",
    "software",
    "equipamento",
    "laudo",
    "prontuário",
    "clinica",
    "clínica",
)

NICHE_RULES = [
    ("Diagnóstico por imagem", ("imagem", "diagnóstico", "diagnostico", "raio", "ressonância", "ressonancia", "tomografia", "ultrassom")),
    ("Laboratórios", ("laboratório", "laboratorio", "análises", "analises", "exame")),
    ("Clínicas e saúde", ("clínica", "clinica", "saúde", "saude", "médic", "medic", "consultório", "consultorio")),
    ("Hospitais", ("hospital", "santa casa", "pronto atendimento")),
    ("Odontologia", ("odonto", "dent", "oral", "sorriso")),
    ("Mineração e indústria", ("mineração", "mineracao", "industrial", "indústria", "industria", "metal", "fábrica", "fabrica")),
    ("Contabilidade", ("contab", "contabilidade", "contador")),
    ("Advocacia", ("advoc", "juríd", "jurid", "direito")),
    ("Educação", ("escola", "educação", "educacao", "colégio", "colegio", "faculdade")),
    ("Comércio local", ("loja", "mercado", "comércio", "comercio", "varejo")),
    ("Tecnologia", ("tecnologia", "software", "sistema", "informática", "informatica")),
    ("Serviços corporativos", ("serviço", "servico", "consultoria")),
]


def _row_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return normalize_text(value)


def _plain(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _norm(value))
    return "".join(char for char in text if not unicodedata.combining(char))


def _name_similarity(a: Any, b: Any) -> float:
    left = re.sub(r"[^a-z0-9 ]+", "", _plain(a))
    right = re.sub(r"[^a-z0-9 ]+", "", _plain(b))
    if not left or not right:
        return 0.0
    ratio = SequenceMatcher(None, left, right).ratio()
    left_terms = {term for term in left.split() if len(term) >= 4}
    right_terms = {term for term in right.split() if len(term) >= 4}
    if left_terms and right_terms:
        overlap = len(left_terms & right_terms) / min(len(left_terms), len(right_terms))
        ratio = max(ratio, overlap)
    return ratio


def _lead_blob(lead: dict[str, Any]) -> str:
    return " ".join(
        _norm(lead.get(key))
        for key in ("name", "company", "segment", "city", "origin", "notes")
        if lead.get(key)
    )


def _lead_completeness(lead: dict[str, Any]) -> int:
    fields = ("name", "company", "phone", "whatsapp", "email", "city", "segment", "origin", "status", "notes")
    return sum(1 for field in fields if _text(lead.get(field)))


def _snapshot_counts(lead_ids: list[int]) -> dict[int, dict[str, int]]:
    counts = {lead_id: {"interactions": 0, "proposals": 0, "attachments": 0} for lead_id in lead_ids}
    if not lead_ids:
        return counts
    placeholders = ",".join(["?"] * len(lead_ids))
    with get_conn() as conn:
        for table, key in (("interactions", "interactions"), ("proposals", "proposals"), ("attachments", "attachments")):
            rows = conn.execute(
                f"SELECT lead_id, COUNT(*) AS total FROM {table} WHERE lead_id IN ({placeholders}) GROUP BY lead_id",
                tuple(lead_ids),
            ).fetchall()
            for row in rows:
                counts.setdefault(_int(row["lead_id"]), {"interactions": 0, "proposals": 0, "attachments": 0})[key] = _int(row["total"])
    return counts


def _pair_duplicate_reason(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str] | None:
    phones_a = {normalize_phone(a.get("phone")), normalize_phone(a.get("whatsapp"))} - {""}
    phones_b = {normalize_phone(b.get("phone")), normalize_phone(b.get("whatsapp"))} - {""}
    if phones_a & phones_b:
        return "Alta", "mesmo telefone ou WhatsApp"
    if _norm(a.get("email")) and _norm(a.get("email")) == _norm(b.get("email")):
        return "Alta", "mesmo e-mail"

    similarity = _name_similarity(a.get("name"), b.get("name"))
    same_city = bool(_norm(a.get("city")) and _norm(a.get("city")) == _norm(b.get("city")))
    same_segment = bool(_norm(a.get("segment")) and _norm(a.get("segment")) == _norm(b.get("segment")))
    same_company_city = bool(_name_similarity(a.get("company"), b.get("company")) >= 0.84 and same_city)

    if similarity >= 0.86 and (same_city or same_segment or same_company_city):
        return "Média", "nome semelhante com cidade, segmento ou empresa compatível"
    if similarity >= 0.92:
        return "Baixa", "nome muito parecido"
    return None


def _group_confidence(reasons: list[dict[str, str]]) -> str:
    if any(reason["confidence"] == "Alta" for reason in reasons):
        return "Alta"
    if any(reason["confidence"] == "Média" for reason in reasons):
        return "Média"
    return "Baixa"


def _idempotency_key(prefix: str, lead_ids: list[int]) -> str:
    raw = f"{prefix}:" + ",".join(str(item) for item in sorted(lead_ids))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _duplicate_group_resolution_markers(lead_ids: list[int], merge_key: str) -> tuple[str, str]:
    return (
        f"{DEDUP_MARKER_PREFIX}{merge_key}]",
        f"{NOT_DUP_MARKER_PREFIX}{_idempotency_key('not-duplicate', lead_ids)}]",
    )


def _duplicate_group_is_resolved(conn, lead_ids: list[int], merge_key: str) -> bool:
    markers = _duplicate_group_resolution_markers(lead_ids, merge_key)
    placeholders = ",".join(["?"] * len(lead_ids))
    marker_clause = " OR ".join(["summary LIKE ?"] * len(markers))
    row = conn.execute(
        f"""
        SELECT id
        FROM interactions
        WHERE lead_id IN ({placeholders})
          AND ({marker_clause})
        LIMIT 1
        """,
        tuple(lead_ids) + tuple(f"%{marker}%" for marker in markers),
    ).fetchone()
    return row is not None


def build_ai_operations_snapshot() -> dict[str, Any]:
    leads = [_row_dict(row) for row in list_leads()]
    lead_ids = [_int(lead.get("id")) for lead in leads]
    return {
        "leads": leads,
        "counts": _snapshot_counts(lead_ids),
    }


def detect_duplicate_groups(snapshot: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    snapshot = snapshot or build_ai_operations_snapshot()
    leads = snapshot.get("leads") or []
    by_id = {_int(lead.get("id")): lead for lead in leads}
    parent = {lead_id: lead_id for lead_id in by_id}
    pair_reasons: dict[tuple[int, int], dict[str, str]] = {}

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(a: int, b: int) -> None:
        root_a = find(a)
        root_b = find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for index, left in enumerate(leads):
        for right in leads[index + 1 :]:
            left_id = _int(left.get("id"))
            right_id = _int(right.get("id"))
            result = _pair_duplicate_reason(left, right)
            if not result:
                continue
            confidence, reason = result
            pair_reasons[(min(left_id, right_id), max(left_id, right_id))] = {"confidence": confidence, "reason": reason}
            union(left_id, right_id)

    grouped_ids: dict[int, list[int]] = {}
    for lead_id in by_id:
        grouped_ids.setdefault(find(lead_id), []).append(lead_id)

    groups: list[dict[str, Any]] = []
    for ids in grouped_ids.values():
        if len(ids) < 2:
            continue
        reasons = [
            value
            for pair, value in pair_reasons.items()
            if pair[0] in ids and pair[1] in ids
        ]
        leads_in_group = [by_id[lead_id] for lead_id in ids]
        group = {
            "group_id": _idempotency_key("duplicate-group", ids),
            "lead_ids": sorted(ids),
            "leads": leads_in_group,
            "confidence": _group_confidence(reasons),
            "reason": "; ".join(sorted({item["reason"] for item in reasons})) or "possível duplicidade operacional",
        }
        group["merge_plan"] = prepare_merge_plan(group, snapshot)
        with get_conn() as conn:
            if _duplicate_group_is_resolved(conn, group["lead_ids"], group["merge_plan"]["idempotency_key"]):
                continue
        groups.append(group)

    confidence_order = {"Alta": 0, "Média": 1, "Baixa": 2}
    return sorted(groups, key=lambda item: (confidence_order.get(item["confidence"], 9), item["lead_ids"]))


def prepare_merge_plan(group: dict[str, Any], snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = snapshot or build_ai_operations_snapshot()
    counts = snapshot.get("counts") or {}
    leads = [dict(lead) for lead in group.get("leads") or []]
    principal = max(
        leads,
        key=lambda lead: (
            _lead_completeness(lead),
            counts.get(_int(lead.get("id")), {}).get("interactions", 0)
            + counts.get(_int(lead.get("id")), {}).get("proposals", 0)
            + counts.get(_int(lead.get("id")), {}).get("attachments", 0),
            _int(lead.get("score")),
            -_int(lead.get("id")),
        ),
    )
    duplicate_ids = [_int(lead.get("id")) for lead in leads if _int(lead.get("id")) != _int(principal.get("id"))]
    fields = ("name", "company", "phone", "whatsapp", "email", "city", "segment", "origin", "status", "notes")
    comparisons = []
    fields_to_update: dict[str, Any] = {}
    for field in fields:
        principal_value = _text(principal.get(field))
        duplicate_values = [_text(lead.get(field)) for lead in leads if _int(lead.get("id")) in duplicate_ids and _text(lead.get(field))]
        suggested = "manter principal"
        if field == "notes" and duplicate_values:
            suggested = "concatenar observações"
        elif not principal_value and duplicate_values:
            fields_to_update[field] = duplicate_values[0]
            suggested = "completar principal"
        comparisons.append({
            "field": field,
            "principal": principal_value or "-",
            "duplicates": " | ".join(duplicate_values) or "-",
            "suggested_action": suggested,
        })

    lead_ids = [_int(lead.get("id")) for lead in leads]
    return {
        "idempotency_key": _idempotency_key("merge", lead_ids),
        "principal_id": _int(principal.get("id")),
        "principal_name": principal.get("name") or "Contato",
        "duplicate_ids": duplicate_ids,
        "confidence": group.get("confidence") or "Baixa",
        "reason": group.get("reason") or "possível duplicidade operacional",
        "risk": "Revisar campos antes de confirmar. Nenhum lead será excluído.",
        "recommended_action": "Executar merge aprovado" if duplicate_ids else "Revisar grupo",
        "comparisons": comparisons,
        "fields_to_update": fields_to_update,
    }


def _interaction_exists(conn, lead_id: int, marker: str) -> bool:
    row = conn.execute(
        "SELECT id FROM interactions WHERE lead_id = ? AND summary LIKE ? LIMIT 1",
        (lead_id, f"%{marker}%"),
    ).fetchone()
    return row is not None


def _insert_internal_interaction(conn, lead_id: int, kind: str, summary: str) -> int:
    cur = conn.execute(
        "INSERT INTO interactions (lead_id, kind, summary, channel, pending) VALUES (?, ?, ?, ?, ?)",
        (lead_id, kind, summary, "manual", 1),
    )
    interaction_id = cur.lastrowid
    conn.execute(
        "INSERT INTO audit_events (event_type, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
        ("central_ia_internal_record", "interaction", str(interaction_id), kind),
    )
    return int(interaction_id)


def execute_approved_merge(plan: dict[str, Any], approved: bool = False) -> dict[str, Any]:
    if not approved:
        return {"applied": False, "created": 0, "message": "Confirmação do operador obrigatória."}
    principal_id = _int(plan.get("principal_id"))
    duplicate_ids = [_int(item) for item in plan.get("duplicate_ids") or [] if _int(item)]
    if not principal_id or not duplicate_ids:
        return {"applied": False, "created": 0, "message": "Plano de merge incompleto."}

    marker = f"{DEDUP_MARKER_PREFIX}{plan.get('idempotency_key')}]"
    with get_conn() as conn:
        if _interaction_exists(conn, principal_id, marker):
            return {"applied": True, "created": 0, "message": "Merge já registrado anteriormente."}

        principal = conn.execute("SELECT * FROM leads WHERE id = ?", (principal_id,)).fetchone()
        if principal is None:
            return {"applied": False, "created": 0, "message": "Lead principal não encontrado."}
        principal_dict = _row_dict(principal)

        updated_fields: list[str] = []
        update_values: dict[str, Any] = {}
        for field, value in (plan.get("fields_to_update") or {}).items():
            if field not in {"company", "phone", "whatsapp", "email", "city", "segment", "origin", "status", "notes"}:
                continue
            if not _text(principal_dict.get(field)) and _text(value):
                update_values[field] = value
                updated_fields.append(field)

        duplicate_rows = conn.execute(
            f"SELECT * FROM leads WHERE id IN ({','.join(['?'] * len(duplicate_ids))})",
            tuple(duplicate_ids),
        ).fetchall()
        duplicate_names = [f"#{row['id']} {row['name']}" for row in duplicate_rows]
        duplicate_notes = []
        for row in duplicate_rows:
            note = _text(row["notes"])
            if note:
                duplicate_notes.append(f"#{row['id']} {row['name']}: {note}")
        if duplicate_notes:
            current_notes = _text(principal_dict.get("notes"))
            merged_note = "\n".join([f"{MERGED_NOTE_PREFIX} #{item}" for item in duplicate_notes])
            if merged_note not in current_notes:
                update_values["notes"] = "\n".join(part for part in [current_notes, merged_note] if part)
                updated_fields.append("notes")

        if update_values:
            assignments = ", ".join(f"{field} = ?" for field in update_values)
            conn.execute(
                f"UPDATE leads SET {assignments} WHERE id = ?",
                tuple(update_values.values()) + (principal_id,),
            )

        for table in ("interactions", "proposals", "attachments"):
            conn.execute(
                f"UPDATE {table} SET lead_id = ? WHERE lead_id IN ({','.join(['?'] * len(duplicate_ids))})",
                (principal_id, *duplicate_ids),
            )

        for duplicate_id in duplicate_ids:
            existing_note = conn.execute("SELECT notes FROM leads WHERE id = ?", (duplicate_id,)).fetchone()
            old_note = _text(existing_note["notes"] if existing_note else "")
            duplicate_marker = f"{MERGED_NOTE_PREFIX} #{principal_id}."
            if duplicate_marker not in old_note:
                new_note = "\n".join(part for part in [old_note, duplicate_marker] if part)
                conn.execute("UPDATE leads SET notes = ? WHERE id = ?", (new_note, duplicate_id))

        summary = (
            f"{marker} Merge aprovado pelo operador. Principal: #{principal_id} {plan.get('principal_name')}. "
            f"Duplicados: {', '.join(duplicate_names)}. Campos atualizados: {', '.join(sorted(set(updated_fields))) or 'nenhum'}."
        )
        _insert_internal_interaction(conn, principal_id, "Central IA - merge aprovado", summary)
    return {"applied": True, "created": 1, "message": "Merge aprovado registrado internamente."}


def register_not_duplicate(group: dict[str, Any], approved: bool = False) -> dict[str, Any]:
    if not approved:
        return {"applied": False, "created": 0, "message": "Confirmação do operador obrigatória."}
    lead_ids = [_int(item) for item in group.get("lead_ids") or [] if _int(item)]
    if not lead_ids:
        return {"applied": False, "created": 0, "message": "Grupo sem contatos."}
    principal_id = lead_ids[0]
    marker = f"{NOT_DUP_MARKER_PREFIX}{_idempotency_key('not-duplicate', lead_ids)}]"
    with get_conn() as conn:
        if _interaction_exists(conn, principal_id, marker):
            return {"applied": True, "created": 0, "message": "Revisão já registrada anteriormente."}
        summary = f"{marker} Operador registrou que o grupo não deve ser tratado como duplicidade neste momento."
        _insert_internal_interaction(conn, principal_id, "Central IA - não duplicado", summary)
    return {"applied": True, "created": 1, "message": "Revisão registrada internamente."}


def classify_niche(lead: dict[str, Any]) -> dict[str, Any]:
    blob = _lead_blob(lead)
    for niche, terms in NICHE_RULES:
        if any(term in blob for term in terms):
            base_score = 82 if niche in {"Diagnóstico por imagem", "Laboratórios", "Clínicas e saúde"} else 68
            score = min(100, base_score + (_int(lead.get("score")) // 8))
            return {
                "lead_id": _int(lead.get("id")),
                "lead_name": lead.get("name") or "Contato",
                "niche": niche,
                "subniche": lead.get("segment") or niche,
                "score": score,
                "priority": "Alta" if score >= 80 else "Média" if score >= 60 else "Baixa",
                "fit": "Alta" if score >= 80 else "Média" if score >= 60 else "Baixa",
                "approach": _niche_approach(niche),
                "reason": f"Classificação por nome, segmento, cidade, origem e observações.",
            }
    score = min(55, max(30, _int(lead.get("score"))))
    return {
        "lead_id": _int(lead.get("id")),
        "lead_name": lead.get("name") or "Contato",
        "niche": "Outros",
        "subniche": lead.get("segment") or "Sem subnicho claro",
        "score": score,
        "priority": "Baixa",
        "fit": "Baixa",
        "approach": "abordagem consultiva inicial para entender operação e dependência de TI",
        "reason": "Sem regra clara de nicho na carteira.",
    }


def _niche_approach(niche: str) -> str:
    if niche in {"Diagnóstico por imagem", "Laboratórios", "Clínicas e saúde", "Hospitais"}:
        return "abordagem consultiva sobre suporte preventivo, backup, rede e estabilidade operacional"
    if niche == "Odontologia":
        return "abordagem sobre manutenção, rede, Wi-Fi e proteção de dados"
    if niche in {"Advocacia", "Contabilidade"}:
        return "abordagem sobre backup, segurança e continuidade dos arquivos"
    return "abordagem consultiva sobre suporte, disponibilidade e prevenção de falhas"


def score_opportunity(lead: dict[str, Any]) -> dict[str, Any]:
    niche = classify_niche(lead)
    status = _norm(lead.get("status"))
    blob = _lead_blob(lead)
    score = 25 + (_int(lead.get("score")) // 2)
    if niche["niche"] in {"Diagnóstico por imagem", "Laboratórios", "Clínicas e saúde", "Hospitais"}:
        score += 25
    if any(term in blob for term in TECH_DEPENDENCY_TERMS):
        score += 15
    if "proposta" in status or "negociação" in status or "negociacao" in status:
        score += 15
    if lead.get("next_followup"):
        score += 8
    score = max(0, min(100, score))
    confidence = "Alta" if _text(lead.get("segment")) or _text(lead.get("notes")) else "Média" if _text(lead.get("city")) else "Baixa"
    return {
        "lead_id": _int(lead.get("id")),
        "lead_name": lead.get("name") or "Contato",
        "score": score,
        "confidence": confidence,
        "temperature": "Quente" if score >= 80 else "Morno" if score >= 55 else "Frio",
        "priority": "Alta" if score >= 80 else "Média" if score >= 55 else "Baixa",
        "next_best_action": _opportunity_next_action(niche["niche"], score),
        "reason": f"{niche['niche']} com aderência {niche['fit']} e sinais de dependência operacional de TI.",
        "impact": "Prioriza contatos com maior chance de avanço comercial consultivo.",
        "suggested_message": f"Preparar abordagem consultiva para {lead.get('name') or 'o contato'} sobre estabilidade, suporte e prevenção.",
        "idempotency_key": _idempotency_key("opportunity", [_int(lead.get("id")), score]),
    }


def _opportunity_next_action(niche: str, score: int) -> str:
    if score >= 80:
        return f"retorno consultivo para {niche.lower()} com foco em suporte preventivo e continuidade"
    if score >= 55:
        return "preparar qualificação comercial e mapear dependência de TI"
    return "manter carteira organizada e aguardar sinal de prioridade"


def build_opportunity_analysis(snapshot: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    snapshot = snapshot or build_ai_operations_snapshot()
    analyses = [score_opportunity(lead) for lead in snapshot.get("leads") or []]
    return sorted(analyses, key=lambda item: (-item["score"], item["lead_name"]))


def build_niche_segmentation(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = snapshot or build_ai_operations_snapshot()
    rows = [classify_niche(lead) for lead in snapshot.get("leads") or []]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["niche"], []).append(row)
    summary = []
    for niche, items in grouped.items():
        avg_score = round(mean(item["score"] for item in items), 1)
        representative = max(items, key=lambda item: (item["score"], -item["lead_id"]))
        summary.append({
            "niche": niche,
            "total": len(items),
            "average_score": avg_score,
            "hot": sum(1 for item in items if item["score"] >= 80),
            "warm": sum(1 for item in items if 55 <= item["score"] < 80),
            "cold": sum(1 for item in items if item["score"] < 55),
            "priority": "Alta" if avg_score >= 80 else "Média" if avg_score >= 60 else "Baixa",
            "recommended_action": _niche_approach(niche),
            "representative_lead_id": representative["lead_id"],
            "representative_lead_name": representative["lead_name"],
        })
    return {
        "rows": rows,
        "summary": sorted(summary, key=lambda item: (-item["average_score"], item["niche"])),
    }


def apply_approved_opportunity_record(analysis: dict[str, Any], approved: bool = False) -> dict[str, Any]:
    if not approved:
        return {"applied": False, "created": 0, "message": "Confirmação do operador obrigatória."}
    lead_id = _int(analysis.get("lead_id"))
    marker = f"{OPPORTUNITY_MARKER_PREFIX}{analysis.get('idempotency_key')}]"
    with get_conn() as conn:
        if _interaction_exists(conn, lead_id, marker):
            return {"applied": True, "created": 0, "message": "Análise já registrada anteriormente."}
        summary = (
            f"{marker} Análise IA aprovada. Score: {analysis.get('score')}. "
            f"Prioridade: {analysis.get('priority')}. Próxima ação: {analysis.get('next_best_action')}. "
            f"Motivo: {analysis.get('reason')}"
        )
        _insert_internal_interaction(conn, lead_id, "Central IA - oportunidade", summary)
    return {"applied": True, "created": 1, "message": "Análise registrada internamente."}


def apply_approved_niche_record(niche_summary: dict[str, Any], approved: bool = False) -> dict[str, Any]:
    if not approved:
        return {"applied": False, "created": 0, "message": "Confirmação do operador obrigatória."}
    niche = niche_summary.get("niche") or "Outros"
    marker = f"{NICHE_MARKER_PREFIX}{hashlib.sha256(niche.encode('utf-8')).hexdigest()[:12]}]"
    lead_id = _int(niche_summary.get("representative_lead_id"))
    with get_conn() as conn:
        lead = conn.execute("SELECT id FROM leads WHERE id = ? LIMIT 1", (lead_id,)).fetchone() if lead_id else None
        if lead is None:
            if conn.execute("SELECT id FROM leads LIMIT 1").fetchone() is None:
                return {"applied": False, "created": 0, "message": "Carteira vazia."}
            return {"applied": False, "created": 0, "message": "Lead representativo do nicho não encontrado."}
        if _interaction_exists(conn, lead_id, marker):
            return {"applied": True, "created": 0, "message": "Análise de nicho já registrada anteriormente."}
        summary = (
            f"{marker} Análise de nicho aprovada. Nicho: {niche}. "
            f"Leads: {niche_summary.get('total')}. Score médio: {niche_summary.get('average_score')}. "
            f"Ação recomendada: {niche_summary.get('recommended_action')}."
        )
        _insert_internal_interaction(conn, lead_id, "Central IA - nicho", summary)
    return {"applied": True, "created": 1, "message": "Análise de nicho registrada internamente."}
