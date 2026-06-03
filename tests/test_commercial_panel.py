import ast
from urllib.parse import parse_qs, quote, unquote, urlparse

from operia_crm.database.db import get_conn
from operia_crm.services.commercial_panel import (
    apply_approved_commercial_actions,
    build_commercial_panel_snapshot,
    prepare_ai_commercial_actions,
)
from operia_crm.services.commercial_workflow import (
    apply_approved_work_package,
    build_leads_operational_view,
    deduplicate_work_actions,
)
from operia_crm.services.core import create_lead


def _load_app_whatsapp_helpers():
    source = open("app.py", encoding="utf-8").read()
    tree = ast.parse(source)
    helper_names = {
        "normalize_phone_for_whatsapp",
        "build_whatsapp_web_url",
        "build_whatsapp_app_url",
        "build_whatsapp_business_android_intent",
        "build_whatsapp_business_android_intent_alt",
        "parse_email_subject_body",
        "build_gmail_compose_url",
        "build_mailto_url",
        "is_valid_email_for_compose",
        "compose_urls",
        "selected_lead_email",
    }
    namespace = {"re": __import__("re"), "quote": quote}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in helper_names:
            exec(compile(ast.Module([node], []), "app.py", "exec"), namespace)
    return namespace


def _make_lead(name, status, score=0, next_followup=None, phone="", email=""):
    lead_id = create_lead({"name": name, "origin": "Site", "status": status, "phone": phone, "email": email, "next_followup": next_followup})
    with get_conn() as conn:
        conn.execute("UPDATE leads SET score=? WHERE id=?", (score, lead_id))
    return lead_id


def test_snapshot_empty_wallet(isolated_env):
    snap = build_commercial_panel_snapshot()
    assert snap["total_contatos"] == 0
    assert snap["oportunidades_em_alta"] == 0


def test_snapshot_new_contacts(isolated_env):
    _make_lead("Novo", "Novo lead", score=30)
    snap = build_commercial_panel_snapshot()
    assert snap["contatos_novos"] >= 1


def test_snapshot_proposal_and_negotiation(isolated_env):
    _make_lead("P1", "Proposta enviada", score=75)
    _make_lead("N1", "Negociação", score=80)
    snap = build_commercial_panel_snapshot()
    assert snap["contatos_proposta_enviada"] >= 1
    assert snap["contatos_em_negociacao"] >= 1
    assert snap["oportunidades_em_alta"] >= 2


def test_calculations_returns_and_open_proposals(isolated_env):
    lead_id = _make_lead("P2", "Proposta enviada", score=72, next_followup="2026-01-01")
    with get_conn() as conn:
        conn.execute("INSERT INTO proposals (lead_id, number, status, total_value, content) VALUES (?, ?, ?, ?, ?)", (lead_id, "PROP-9999", "Aberta", 100, "x"))
    snap = build_commercial_panel_snapshot()
    assert snap["retornos_a_fazer"] >= 1
    assert snap["propostas_em_aberto"] >= 1


def test_open_proposal_table_drives_card_funnel_and_opportunity(isolated_env):
    lead_id = _make_lead("P3", "Novo lead", score=20)
    with get_conn() as conn:
        conn.execute("INSERT INTO proposals (lead_id, number, status, total_value, content) VALUES (?, ?, ?, ?, ?)", (lead_id, "PROP-1000", "Aberta", 100, "x"))
    snap = build_commercial_panel_snapshot()
    assert snap["propostas_em_aberto"] == 1
    assert snap["contatos_proposta_enviada"] == 1
    assert snap["funnel"]["Proposta/cardápio enviado"] == 1
    assert snap["funnel"]["Novo contato"] == 0
    assert snap["oportunidades_em_alta"] == 1


def test_prepare_actions_limits_and_alerts(isolated_env):
    for i in range(7):
        _make_lead(f"L{i}", "Proposta enviada", score=80)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    assert pack["main_action"]
    assert len(pack["alerts"]) <= 3
    assert len(pack["prepared_actions"]) <= 5
    assert len(pack["day_queue"]) <= 5
    assert pack["package_signature"]
    assert all(action["impact"] for action in pack["prepared_actions"])


def test_package_has_day_queue_impact_and_suggested_message(isolated_env):
    lead_id = _make_lead("Cliente Proposta", "Proposta enviada", score=80)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    action = pack["day_queue"][0]
    assert action["lead_id"] == lead_id
    assert action["impact"]
    assert action["suggested_message"]
    assert action["fingerprint"]
    assert pack["package_signature"]


def test_incomplete_registration_action(isolated_env):
    lead_id = _make_lead("Sem Canal", "Qualificar", score=20)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    actions = pack["prepared_actions"]
    assert actions[0]["lead_id"] == lead_id
    assert actions[0]["type"] == "cadastro_incompleto"
    assert actions[0]["impact"]


def test_ai_success_does_not_influence_deterministic_recommendation(isolated_env, monkeypatch):
    lead_id = _make_lead("L", "Proposta enviada", score=80)

    def fake_run(*args, **kwargs):
        return {"success": True, "used_fallback": False, "content": "Ação principal: Outra ação."}

    monkeypatch.setattr("operia_crm.services.commercial_panel.run_assisted_action", fake_run)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    assert pack["main_action"] == "Retornar primeiro propostas/cardápios em aberto antes de iniciar novos contatos."
    assert pack["prepared_actions"][0]["lead_id"] == lead_id


def test_ai_fallback_or_error_uses_local(isolated_env, monkeypatch):
    def fake_run(*args, **kwargs):
        return {"success": True, "used_fallback": True, "content": "x", "error": "falha"}

    monkeypatch.setattr("operia_crm.services.commercial_panel.run_assisted_action", fake_run)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    assert pack["main_action"]


def test_invalid_ai_content_does_not_break(isolated_env, monkeypatch):
    def fake_run(*args, **kwargs):
        return {"success": True, "used_fallback": False, "content": None}

    monkeypatch.setattr("operia_crm.services.commercial_panel.run_assisted_action", fake_run)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    assert isinstance(pack, dict)
    assert pack["main_action"]


def test_no_technical_metadata_in_panel_return(isolated_env, monkeypatch):
    def fake_run(*args, **kwargs):
        return {"success": True, "used_fallback": False, "content": "provider: x\nmodel: y\nAção principal: Fazer retornos hoje."}

    monkeypatch.setattr("operia_crm.services.commercial_panel.run_assisted_action", fake_run)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    blob = str(pack).lower()
    for bad in ["provider", "model", "fallback", "token", "sqlite", "banco", "database", "path", "log", "debug", "stacktrace", "erro técnico"]:
        assert bad not in blob


def test_funnel_totals_match_total_contacts(isolated_env):
    _make_lead("Novo", "Novo lead", score=20)
    _make_lead("Contato", "Qualificar", score=20)
    _make_lead("Neg", "Negociação", score=80)
    _make_lead("Ganho", "Ganho", score=90)
    lead_id = _make_lead("Prop", "Novo lead", score=20)
    with get_conn() as conn:
        conn.execute("INSERT INTO proposals (lead_id, number, status, total_value, content) VALUES (?, ?, ?, ?, ?)", (lead_id, "PROP-2000", "Aberta", 100, "x"))
    snap = build_commercial_panel_snapshot()
    assert sum(snap["funnel"].values()) == snap["total_contatos"]


def test_apply_approved_only_internal(isolated_env):
    lead_id = _make_lead("A", "Negociação", score=80)
    created = apply_approved_commercial_actions([
        {"lead_id": lead_id, "title": "Criar retorno pendente", "content": "Retornar contato", "impact": "Avança negociação"},
        {"lead_id": None, "title": "inválida", "content": "x"},
    ])
    assert created == 1
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM interactions").fetchall()
        assert len(rows) == 1
        assert "Preparado pela IA" in rows[0]["summary"]
        assert "Impacto:" in rows[0]["summary"]


def test_apply_approved_commercial_actions_is_idempotent(isolated_env):
    _make_lead("A", "Negociação", score=80)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    first = apply_approved_commercial_actions(pack["prepared_actions"])
    second = apply_approved_commercial_actions(pack["prepared_actions"])
    assert first == 1
    assert second == 0
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM interactions").fetchall()
        assert len(rows) == 1


def test_reapplying_same_package_creates_zero_new_actions(isolated_env):
    _make_lead("P", "Proposta enviada", score=80)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    assert apply_approved_commercial_actions(pack["prepared_actions"]) == 1
    assert apply_approved_commercial_actions(pack["prepared_actions"]) == 0


def test_package_actions_have_operational_fields(isolated_env):
    _make_lead("Cliente Operacional", "Negociação", score=80, phone="37999990000")
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    action = pack["prepared_actions"][0]
    assert action["weight"] in {"Alta", "Média", "Baixa"}
    assert action["reason"]
    assert action["impact"]
    assert action["prepared_content"]
    assert action["state"] in {"aguardando liberação", "registrada", "bloqueada por duplicidade"}
    assert action["idempotency_key"]


def test_without_approval_nothing_is_registered(isolated_env):
    _make_lead("Sem Aprovação", "Negociação", score=80)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    assert apply_approved_work_package(pack, approved=False) == 0
    with get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) AS total FROM interactions").fetchone()["total"] == 0


def test_approved_package_skips_duplicate_blocked_actions(isolated_env):
    _make_lead("Duplicado", "Novo lead", score=30, phone="37999990000")
    _make_lead("Duplicado cópia", "Novo lead", score=30, phone="37999990000")
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    assert any(action["state"] == "bloqueada por duplicidade" for action in pack["prepared_actions"])
    assert apply_approved_work_package(pack, approved=True) == 0


def test_duplicate_blocks_do_not_hide_productive_actions(isolated_env):
    for index in range(6):
        _make_lead(f"Duplicado {index}", "Novo lead", score=30, phone="37999990000")
    productive_id = _make_lead("Negociação válida", "Negociação", score=80, phone="37988880000")

    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())

    assert any(action["lead_id"] == productive_id for action in pack["prepared_actions"])
    assert any(action["state"] == "bloqueada por duplicidade" for action in pack["prepared_actions"])
    assert pack["day_queue"]
    assert all(action["state"] != "bloqueada por duplicidade" for action in pack["day_queue"])


def test_work_action_deduplication_uses_idempotency_key(isolated_env):
    actions = [
        {"idempotency_key": "same", "lead_id": 1, "type": "criar_retorno_pendente"},
        {"idempotency_key": "same", "lead_id": 1, "type": "criar_retorno_pendente"},
        {"idempotency_key": "other", "lead_id": 1, "type": "registrar_interacao_interna"},
    ]
    assert [action["idempotency_key"] for action in deduplicate_work_actions(actions)] == ["same", "other"]


def test_leads_operational_view_flags_incomplete_and_duplicates(isolated_env):
    _make_lead("Ana", "Novo lead", score=20, phone="37999990000")
    _make_lead("Ana Duplicada", "Novo lead", score=20, phone="37999990000")
    _make_lead("Sem Canal", "Qualificar", score=20)
    rows = build_leads_operational_view()
    assert any(row["Risco de duplicidade"] != "Sem alerta" for row in rows)
    assert any(row["Próxima ação sugerida"] == "Sinalizar contato incompleto" for row in rows)


def test_panel_package_has_simple_evidence_without_technical_terms(isolated_env):
    _make_lead("Evidência", "Proposta enviada", score=80)
    pack = prepare_ai_commercial_actions(build_commercial_panel_snapshot())
    evidence = " ".join(pack["evidence"]).lower()
    assert "json" not in evidence
    for bad in ["provider", "model", "fallback", "sqlite", "database", "debug", "path", "token", "api error", "stacktrace"]:
        assert bad not in evidence


def test_app_commercial_areas_do_not_expose_removed_ai_controls():
    source = open("app.py", encoding="utf-8").read()
    for removed in [
        "IA: analisar lead",
        "IA: próxima ação",
        "IA: WhatsApp",
        "IA: e-mail",
        "provider=",
        "model=",
        "source=",
        "fallback=",
        "error=",
        "Atualizar leitura da carteira",
    ]:
        assert removed not in source
    assert "Atualizar análise IA da carteira" in source
    assert "Preparar abordagem para revisão" in source
    assert "Preparar próxima ação" in source
    assert "Registrar mensagem preparada" in source


def test_duplicate_lead_branch_does_not_expose_normal_commercial_ctas():
    source = open("app.py", encoding="utf-8").read()
    after_condition = source.split("if duplicate_risk_active:", 1)[1]
    duplicate_branch, normal_branch = after_condition.split("\n        else:\n            c1, c2 = st.columns(2)", 1)

    assert "Contato com risco de duplicidade. Revise o cadastro antes de preparar nova ação comercial." in duplicate_branch
    assert "Registrar revisão de duplicidade" in duplicate_branch
    assert "register_interaction" in duplicate_branch
    assert "Preparar abordagem para revisão" not in duplicate_branch
    assert "Preparar próxima ação" not in duplicate_branch
    normal_branch = "c1, c2 = st.columns(2)" + normal_branch
    assert "Preparar abordagem para revisão" in normal_branch
    assert "Preparar próxima ação" in normal_branch


def test_premium_commercial_panel_keeps_human_review_contract():
    source = open("app.py", encoding="utf-8").read()
    required = [
        "OperIA CRM — Empório",
        "Modo operacional para restaurante: retornos, eventos, encomendas, reservas e atendimento corporativo com revisão humana.",
        "Retornos de hoje",
        "Eventos próximos",
        "Proposta/cardápio",
        "IA com revisão",
        "Oportunidades abertas",
        "Oportunidades em alta",
        "Retornos pendentes",
        "Eventos/entregas próximos",
        "Propostas/cardápios aguardando retorno",
        "Valor estimado em aberto",
        "Contatos parados",
        "Existem possíveis duplicidades. Revise antes de liberar novas ações comerciais.",
        "O que o operador deve fazer agora",
        "Tamanho do lote operacional",
        "Lead do lote",
        "#{lead_id} — {name} | {commercial_temperature(item)} | {title}",
        "Mensagem WhatsApp sugerida para o Empório",
        "E-mail sugerido para o Empório",
        "WhatsApp revisado",
        "WhatsApp Web",
        "Gmail",
        "App e-mail",
        "Registrar WhatsApp + D+2",
        "Registrar e-mail + D+3",
        "Pular por agora",
        "Revisei o conteúdo e autorizo apenas o registro manual desta ação",
        "Marque a aprovação antes de registrar a ação no CRM.",
        "Revisei e autorizo apenas o registro interno dessas ações",
        "Confirmar e registrar no CRM",
        "Marque a aprovação antes de registrar as ações no CRM.",
        "commercial_panel_applied_signature",
        "CRM detalhado mantido abaixo em segundo plano. Use apenas para operação detalhada, importação, exportação ou configuração.",
        "Mostrar abas antigas / operação detalhada",
        "Importação CSV inteligente",
        "Backup manual do banco",
        "Inicializar / migrar banco",
        "O app não dispara WhatsApp/e-mail automaticamente. Ele prepara e registra a ação.",
    ]
    for text in required:
        assert text in source


def test_premium_commercial_panel_does_not_trigger_external_channels():
    source = open("app.py", encoding="utf-8").read()
    forbidden = [
        "webbrowser.open",
        "wa.me",
        "api.whatsapp",
        "smtplib",
        "selenium",
        "send_message",
        "sendmail",
        "send_email",
    ]
    for text in forbidden:
        assert text not in source.lower()
    assert "package=com.whatsapp.w4b" in source
    assert "S.browser_fallback_url=" in source
    assert "whatsapp-action-button" in source
    assert "web.whatsapp.com/send?phone=" in source
    assert "accounts.google.com/AccountChooser" in source
    assert "mail.google.com/mail/u/0/?view=cm&fs=1&tf=1" in source
    assert "workspace.google.com" not in source
    assert "mailto:" in source


def test_whatsapp_phone_normalization_and_revised_links():
    helpers = _load_app_whatsapp_helpers()
    assert helpers["normalize_phone_for_whatsapp"]("(37) 99999-9999") == "5537999999999"

    urls = helpers["compose_urls"](
        {"phone": "(37) 99999-9999", "email": "lead@example.com"},
        "Olá, mensagem revisada / teste",
        "Corpo do e-mail",
    )

    assert urls["whatsapp"].startswith("intent://send/?")
    assert "package=com.whatsapp.w4b" in urls["whatsapp"]
    assert "S.browser_fallback_url=" in urls["whatsapp"]
    assert "wa.me" not in urls["whatsapp"]
    assert "whatsapp://send" not in urls["whatsapp"]
    assert "phone=5537999999999" in urls["whatsapp"]
    assert "Ol%C3%A1%2C%20mensagem%20revisada%20%2F%20teste" in urls["whatsapp"]
    assert "https%3A%2F%2Fweb.whatsapp.com%2Fsend%3Fphone%3D5537999999999" in urls["whatsapp"]
    assert urls["whatsapp_web"].startswith("https://web.whatsapp.com/send")
    assert "phone=5537999999999" in urls["whatsapp_web"]
    assert urls["whatsapp_app"].startswith("whatsapp://send?phone=5537999999999")

    business_intent = helpers["build_whatsapp_business_android_intent"](
        "5537999999999",
        "Olá",
        urls["whatsapp_web"],
    )
    assert business_intent.startswith("intent://send/?phone=5537999999999")
    assert "package=com.whatsapp.w4b" in business_intent
    assert "S.browser_fallback_url=" in business_intent
    assert "whatsapp://send" not in business_intent

    alt_intent = helpers["build_whatsapp_business_android_intent_alt"](
        "5537999999999",
        "Olá",
        urls["whatsapp_web"],
    )
    assert alt_intent.startswith("intent://send?phone=5537999999999")
    assert "package=com.whatsapp.w4b" in alt_intent
    assert "S.browser_fallback_url=" in alt_intent


def test_gmail_compose_and_mailto_links_use_reviewed_email_content():
    helpers = _load_app_whatsapp_helpers()
    subject, body = helpers["parse_email_subject_body"]("Assunto: Próximos passos\n\nOlá...")
    assert subject == "Próximos passos"
    assert body == "Olá..."

    gmail_url = helpers["build_gmail_compose_url"](
        "cliente@dominio.com.br",
        "Assunto: Próximos passos\n\nOlá, cliente.\nVamos falar?",
    )
    assert gmail_url.startswith("https://accounts.google.com/AccountChooser")
    assert "service=mail" in gmail_url
    assert "continue=" in gmail_url
    assert "workspace.google.com" not in gmail_url
    continue_url = unquote(parse_qs(urlparse(gmail_url).query)["continue"][0])
    assert "https://mail.google.com/mail/u/0/" in continue_url
    assert "view=cm" in continue_url
    assert "fs=1" in continue_url
    assert "tf=1" in continue_url
    assert "to=" in continue_url
    assert "su=" in continue_url
    assert "body=" in continue_url
    assert "to=cliente@dominio.com.br" in continue_url
    assert "su=Próximos passos" in continue_url
    assert "body=Olá, cliente.\nVamos falar?" in continue_url

    mailto_url = helpers["build_mailto_url"](
        "cliente@dominio.com.br",
        "Assunto: Próximos passos\n\nOlá, cliente.",
    )
    assert mailto_url.startswith("mailto:")
    assert "subject=Pr%C3%B3ximos%20passos" in mailto_url
    assert "body=Ol%C3%A1%2C%20cliente." in mailto_url

    urls = helpers["compose_urls"](
        {"email": "cliente@dominio.com.br", "phone": "(37) 99999-9999"},
        "Mensagem WhatsApp",
        "Assunto: Retorno comercial\n\nCorpo revisado",
    )
    assert urls["gmail"].startswith("https://accounts.google.com/AccountChooser")
    reviewed_continue_url = unquote(parse_qs(urlparse(urls["gmail"]).query)["continue"][0])
    assert "mail.google.com/mail/u/0/" in reviewed_continue_url
    assert "su=Retorno comercial" in reviewed_continue_url
    assert "body=Corpo revisado" in reviewed_continue_url

    missing_email_urls = helpers["compose_urls"](
        {"email": "sem-email", "phone": "(37) 99999-9999"},
        "Mensagem WhatsApp",
        "Assunto: Retorno comercial\n\nCorpo revisado",
    )
    assert missing_email_urls["gmail"] == ""
    assert missing_email_urls["email_app"] == ""
