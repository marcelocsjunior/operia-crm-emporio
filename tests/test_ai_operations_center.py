from operia_crm.database.db import get_conn
from operia_crm.services.ai_operations_center import (
    apply_approved_niche_record,
    apply_approved_opportunity_record,
    build_ai_operations_snapshot,
    build_niche_segmentation,
    build_opportunity_analysis,
    classify_niche,
    detect_duplicate_groups,
    execute_approved_merge,
    prepare_merge_plan,
    register_not_duplicate,
    score_opportunity,
)
from operia_crm.services.core import create_lead


def _lead(name, **extra):
    payload = {
        "name": name,
        "origin": extra.pop("origin", "Site"),
        "status": extra.pop("status", "Novo lead"),
    }
    payload.update(extra)
    return create_lead(payload)


def test_detects_strong_duplicate_by_same_email_phone_or_whatsapp(isolated_env):
    _lead("Clínica Alfa", email="contato@alfa.com", phone="37999990000")
    _lead("Clinica Alfa Unidade", email="contato@alfa.com")
    _lead("Outro Alfa", whatsapp="37999990000")

    groups = detect_duplicate_groups()

    assert groups
    assert groups[0]["confidence"] == "Alta"
    assert "mesmo" in groups[0]["reason"]


def test_detects_medium_duplicate_by_similar_name_and_city(isolated_env):
    _lead("Imagine Diagnóstico por Imagem", city="Formiga", segment="Saúde")
    _lead("Imagine Diagnostico", city="Formiga", segment="Clínica")

    groups = detect_duplicate_groups()

    assert groups
    assert groups[0]["confidence"] in {"Alta", "Média"}


def test_distinct_leads_are_not_strong_duplicates_by_niche_and_city_only(isolated_env):
    _lead("Clínica Alfa", city="BH", segment="Saúde")
    _lead("Laboratório Beta", city="BH", segment="Saúde")

    groups = detect_duplicate_groups()

    assert groups == []


def test_merge_plan_prefers_more_complete_or_historic_principal(isolated_env):
    sparse_id = _lead("Lab Exato", email="lab@example.com")
    complete_id = _lead("Laboratório Exato", email="lab@example.com", phone="37999990000", city="Divinópolis", segment="Laboratório")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO interactions (lead_id, kind, summary, channel, pending) VALUES (?, ?, ?, ?, ?)",
            (complete_id, "Manual", "histórico", "manual", 1),
        )

    group = detect_duplicate_groups()[0]
    plan = prepare_merge_plan(group)

    assert plan["principal_id"] == complete_id
    assert sparse_id in plan["duplicate_ids"]


def test_merge_plan_does_not_overwrite_filled_field_with_blank(isolated_env):
    _lead("Lab A", email="a@example.com", phone="37999990000")
    _lead("Lab A Duplicado", email="a@example.com", phone="")

    plan = detect_duplicate_groups()[0]["merge_plan"]

    assert "phone" not in plan["fields_to_update"]


def test_merge_without_approval_does_not_execute(isolated_env):
    _lead("Lab A", email="a@example.com")
    _lead("Lab A Duplicado", email="a@example.com")
    plan = detect_duplicate_groups()[0]["merge_plan"]

    result = execute_approved_merge(plan, approved=False)

    assert result["applied"] is False
    with get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) AS total FROM interactions").fetchone()["total"] == 0


def test_approved_merge_is_idempotent_and_preserves_related_records(isolated_env):
    _lead("Lab Completo", email="lab@example.com", city="BH")
    duplicate_id = _lead("Lab Completo Dup", email="lab@example.com", phone="37999990000", notes="observação duplicada")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO proposals (lead_id, number, status, total_value, content) VALUES (?, ?, ?, ?, ?)",
            (duplicate_id, "PROP-IA-1", "Aberta", 100, "x"),
        )
        conn.execute(
            "INSERT INTO attachments (lead_id, original_name, saved_name, extension, size_bytes, note) VALUES (?, ?, ?, ?, ?, ?)",
            (duplicate_id, "a.pdf", "a.pdf", ".pdf", 1, ""),
        )

    plan = detect_duplicate_groups()[0]["merge_plan"]
    principal_id = plan["principal_id"]
    first = execute_approved_merge(plan, approved=True)
    second = execute_approved_merge(plan, approved=True)

    assert first["created"] == 1
    assert second["created"] == 0
    with get_conn() as conn:
        assert conn.execute("SELECT lead_id FROM proposals WHERE number = 'PROP-IA-1'").fetchone()["lead_id"] == principal_id
        assert conn.execute("SELECT lead_id FROM attachments WHERE saved_name = 'a.pdf'").fetchone()["lead_id"] == principal_id
        rows = conn.execute("SELECT summary FROM interactions WHERE lead_id = ?", (principal_id,)).fetchall()
        assert sum(1 for row in rows if "[central-ia-dedup:" in row["summary"]) == 1


def test_approved_merge_resolves_duplicate_group(isolated_env):
    _lead("Lab Resolvido", email="resolvido@example.com")
    _lead("Lab Resolvido Unidade", email="resolvido@example.com")
    group = detect_duplicate_groups()[0]

    result = execute_approved_merge(group["merge_plan"], approved=True)

    assert result["created"] == 1
    assert detect_duplicate_groups() == []


def test_register_not_duplicate_creates_internal_audit(isolated_env):
    _lead("Alfa", email="a@example.com")
    _lead("Alfa Dois", email="a@example.com")
    group = detect_duplicate_groups()[0]

    result = register_not_duplicate(group, approved=True)

    assert result["created"] == 1
    with get_conn() as conn:
        assert "[central-ia-not-duplicate:" in conn.execute("SELECT summary FROM interactions").fetchone()["summary"]


def test_register_not_duplicate_resolves_duplicate_group(isolated_env):
    _lead("Beta", email="beta@example.com")
    _lead("Beta Unidade", email="beta@example.com")
    group = detect_duplicate_groups()[0]

    result = register_not_duplicate(group, approved=True)

    assert result["created"] == 1
    assert detect_duplicate_groups() == []


def test_opportunity_scores_health_lab_as_hot(isolated_env):
    lead_id = _lead("Laboratório São Geraldo", segment="Laboratório", notes="backup rede sistema laudo", status="Negociação")
    with get_conn() as conn:
        lead = dict(conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone())

    analysis = score_opportunity(lead)

    assert analysis["temperature"] == "Quente"
    assert analysis["priority"] == "Alta"
    assert analysis["next_best_action"]
    assert analysis["reason"]


def test_approved_opportunity_record_is_idempotent(isolated_env):
    lead_id = _lead("Laboratório São Geraldo", segment="Laboratório", notes="backup rede sistema")
    with get_conn() as conn:
        lead = dict(conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone())
    analysis = score_opportunity(lead)

    first = apply_approved_opportunity_record(analysis, approved=True)
    second = apply_approved_opportunity_record(analysis, approved=True)

    assert first["created"] == 1
    assert second["created"] == 0


def test_niche_classification_rules(isolated_env):
    assert classify_niche({"id": 1, "name": "Laboratório Exato"})["niche"] == "Laboratórios"
    assert classify_niche({"id": 2, "name": "Imagem Diagnóstico"})["niche"] == "Diagnóstico por imagem"
    assert classify_niche({"id": 3, "name": "Odonto Sorriso"})["niche"] == "Odontologia"
    assert classify_niche({"id": 4, "name": "Advocacia Lima"})["niche"] == "Advocacia"
    assert classify_niche({"id": 5, "name": "Contabilidade Real"})["niche"] == "Contabilidade"
    assert classify_niche({"id": 6, "name": "Empresa sem regra"})["niche"] == "Outros"


def test_niche_grouping_and_approved_record(isolated_env):
    _lead("Laboratório Exato", segment="Laboratório")
    _lead("Laboratório Real", segment="Laboratório")
    _lead("Odonto Sorriso", segment="Odontologia")

    segmentation = build_niche_segmentation()
    labs = next(item for item in segmentation["summary"] if item["niche"] == "Laboratórios")

    assert labs["total"] == 2
    assert labs["average_score"] > 0
    first = apply_approved_niche_record(labs, approved=True)
    second = apply_approved_niche_record(labs, approved=True)
    assert first["created"] == 1
    assert second["created"] == 0


def test_approved_niche_record_uses_representative_lead_inside_niche(isolated_env):
    outside_id = _lead("Advocacia Fora", segment="Advocacia")
    lab_id = _lead("Laboratório Dentro", segment="Laboratório", score=80)

    segmentation = build_niche_segmentation()
    labs = next(item for item in segmentation["summary"] if item["niche"] == "Laboratórios")
    result = apply_approved_niche_record(labs, approved=True)

    assert result["created"] == 1
    assert labs["representative_lead_id"] == lab_id
    with get_conn() as conn:
        outside_rows = conn.execute("SELECT summary FROM interactions WHERE lead_id = ?", (outside_id,)).fetchall()
        lab_rows = conn.execute("SELECT summary FROM interactions WHERE lead_id = ?", (lab_id,)).fetchall()
    assert all("[central-ia-niche:" not in row["summary"] for row in outside_rows)
    assert any("[central-ia-niche:" in row["summary"] for row in lab_rows)


def test_ai_operations_snapshot_and_lists_are_lightweight(isolated_env):
    _lead("Lead A")
    snapshot = build_ai_operations_snapshot()

    assert len(snapshot["leads"]) == 1
    assert isinstance(build_opportunity_analysis(snapshot), list)
    assert isinstance(build_niche_segmentation(snapshot)["summary"], list)


def test_app_has_central_ia_without_regressing_validated_tabs():
    source = open("app.py", encoding="utf-8").read()
    assert '"Central IA"' in source
    assert "Atualizar análise da Central IA" in source
    assert "Deduplicação IA" in source
    assert "Análise de oportunidades" in source
    assert "Segmentação por nicho e score" in source
    assert "Painel Comercial" in source
    assert "Leads" in source
    assert "Selecionar arquivo CSV ou XLSX" in source
    assert "Usar arquivo salvo no servidor" in source
