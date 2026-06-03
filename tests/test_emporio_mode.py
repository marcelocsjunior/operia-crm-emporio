from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from operia_crm.database.db import get_conn, init_db
from operia_crm.services.commercial_panel import build_commercial_panel_snapshot, prepare_ai_commercial_actions
from operia_crm.services.core import create_lead, import_deduped_leads
from operia_crm.services.emporio_mode import (
    EMPORIO_STATUSES,
    OPPORTUNITY_TYPES,
    calculate_emporio_priority,
    suggest_emporio_message,
)
from operia_crm.services.import_workflow import analyze_import_dataframe


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
        for index, row in enumerate(self._rows):
            yield index, _FakeRow(row)


def test_emporio_schema_is_idempotent_and_has_fields(isolated_env):
    init_db()
    init_db()
    with get_conn() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(leads)").fetchall()}

    assert {
        "opportunity_type",
        "event_or_delivery_date",
        "estimated_value",
        "people_count",
        "source_channel",
        "emporio_status",
        "next_action",
        "operational_notes",
    }.issubset(columns)


def test_create_lead_persists_emporio_fields(isolated_env):
    lead_id = create_lead(
        {
            "name": "Contato Sintético",
            "origin": "WhatsApp",
            "status": "Novo lead",
            "phone": "37999990000",
            "opportunity_type": "Evento",
            "event_or_delivery_date": (date.today() + timedelta(days=5)).isoformat(),
            "estimated_value": 1500,
            "people_count": 30,
            "source_channel": "Instagram",
            "emporio_status": "Qualificar demanda",
            "next_action": "Enviar cardápio de eventos",
            "operational_notes": "Preferência por almoço.",
        }
    )

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()

    assert row["opportunity_type"] == "Evento"
    assert row["estimated_value"] == 1500
    assert row["people_count"] == 30
    assert row["source_channel"] == "Instagram"
    assert row["emporio_status"] == "Qualificar demanda"
    assert row["next_action"] == "Enviar cardápio de eventos"
    assert row["operational_notes"] == "Preferência por almoço."


def test_import_analysis_recognizes_emporio_columns():
    df = pd.DataFrame(
        [
            {
                "nome": "Contato Sintético",
                "whatsapp": "37999990000",
                "tipo_oportunidade": "Evento",
                "data_evento_ou_entrega": (date.today() + timedelta(days=3)).isoformat(),
                "valor_estimado": "1.250,50",
                "quantidade_pessoas": "25",
                "canal_origem": "Instagram",
                "status_emporio": "Proposta/cardápio enviado",
                "proxima_acao": "Retornar amanhã",
                "observacao_operacional": "Sem dados reais.",
            }
        ]
    )

    analysis = analyze_import_dataframe(df, [])
    recognized = {item["field"] for item in analysis["recognized_columns"]}
    row = analysis["rows"][0]

    assert "opportunity_type" in recognized
    assert "event_or_delivery_date" in recognized
    assert row["tipo_oportunidade"] == "Evento"
    assert row["status_emporio"] == "Proposta/cardápio enviado"
    assert row["acao_prevista"] == "Importar"


def test_import_deduped_leads_with_emporio_columns_and_legacy_still_works(isolated_env):
    legacy = _FakeDf([{"name": "Lead Antigo", "email": "antigo@example.com"}])
    emporio = _FakeDf(
        [
            {
                "nome": "Lead Empório",
                "telefone": "37999990000",
                "tipo_oportunidade": "Cliente corporativo",
                "status_emporio": "Aguardando retorno",
                "valor_estimado": "2500",
            }
        ]
    )

    legacy_summary = import_deduped_leads(legacy, existing=[])
    emporio_summary = import_deduped_leads(emporio, existing=[])

    assert legacy_summary["importados"] == 1
    assert emporio_summary["importados"] == 1
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE name = ?", ("Lead Empório",)).fetchone()
    assert row["opportunity_type"] == "Cliente corporativo"
    assert row["emporio_status"] == "Aguardando retorno"
    assert row["estimated_value"] == 2500


def test_event_within_next_7_days_is_high_priority():
    result = calculate_emporio_priority(
        {
            "opportunity_type": "Evento",
            "event_or_delivery_date": (date.today() + timedelta(days=7)).isoformat(),
            "estimated_value": 300,
            "people_count": 8,
            "emporio_status": "Qualificar demanda",
        }
    )

    assert result["priority"] == "Alta"
    assert result["temperature"] == "Quente"
    assert "evento/entrega nos próximos 7 dias" in result["reasons"]


def test_corporate_or_recurring_opportunity_gets_extra_weight():
    corporate = calculate_emporio_priority({"opportunity_type": "Cliente corporativo", "estimated_value": 1})
    recurring = calculate_emporio_priority({"opportunity_type": "Marmita / refeição recorrente", "estimated_value": 1})
    other = calculate_emporio_priority({"opportunity_type": "Outro", "estimated_value": 1})

    assert corporate["score"] > other["score"]
    assert recurring["score"] > other["score"]


def test_panel_prioritizes_emporio_operational_queue(isolated_env):
    event_id = create_lead(
        {
            "name": "Evento Sintético",
            "origin": "WhatsApp",
            "status": "Novo lead",
            "phone": "37999990000",
            "opportunity_type": "Evento",
            "event_or_delivery_date": (date.today() + timedelta(days=2)).isoformat(),
            "emporio_status": "Qualificar demanda",
        }
    )
    create_lead({"name": "Contato Baixo", "origin": "Site", "status": "Novo lead", "email": "baixo@example.com"})

    snapshot = build_commercial_panel_snapshot()
    package = prepare_ai_commercial_actions(snapshot)

    assert snapshot["eventos_entregas_proximos"] == 1
    assert package["day_queue"][0]["lead_id"] == event_id
    assert package["day_queue"][0]["emporio_priority"] == "Alta"


def test_emporio_messages_are_specific_and_do_not_send():
    assert "proposta/cardápio" in suggest_emporio_message({"name": "Cliente", "emporio_status": "Aguardando retorno"})
    assert "atendimento corporativo" in suggest_emporio_message({"name": "Empresa", "opportunity_type": "Cliente corporativo"})
    assert "refeições recorrentes" in suggest_emporio_message({"name": "Equipe", "opportunity_type": "Marmita / refeição recorrente"})
    assert "revisada pelo operador" in suggest_emporio_message({"name": "Cliente"})


def test_no_automatic_send_function_was_introduced():
    source = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in [
            "app.py",
            "src/operia_crm/services/emporio_mode.py",
            "src/operia_crm/services/commercial_workflow.py",
        ]
    ).lower()
    forbidden = ["smtplib", "selenium", "api.whatsapp", "sendmail", "send_message", "send_email"]
    for item in forbidden:
        assert item not in source


def test_app_exposes_emporio_operational_fields():
    source = Path("app.py").read_text(encoding="utf-8")
    for text in [
        "Tipo de oportunidade",
        "Data do evento/entrega/reserva",
        "Valor estimado",
        "Quantidade de pessoas",
        "Canal de origem",
        "Status Empório",
        "Próxima ação",
        "Observação operacional",
        "Mensagem WhatsApp sugerida para o Empório",
    ]:
        assert text in source


def test_controlled_options_are_available():
    assert OPPORTUNITY_TYPES == [
        "Reserva",
        "Evento",
        "Encomenda",
        "Marmita / refeição recorrente",
        "Cliente corporativo",
        "Parceria",
        "Reativação",
        "Outro",
    ]
    assert EMPORIO_STATUSES == [
        "Novo contato",
        "Qualificar demanda",
        "Proposta/cardápio enviado",
        "Aguardando retorno",
        "Confirmado / fechado",
        "Perdido",
        "Reativar futuramente",
    ]
