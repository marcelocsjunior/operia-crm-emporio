import streamlit as st
from pathlib import Path
from datetime import date, datetime, timedelta
from html import escape, escape as html_escape
from urllib.parse import quote
import re


from operia_crm.ai.assistant import suggest_message
from operia_crm.ai.runtime import run_assisted_action
from operia_crm.auth import apply_streamlit_auth_guard
from operia_crm.database.db import init_db
from operia_crm.services.ai_operations_center import (
    apply_approved_niche_record,
    apply_approved_opportunity_record,
    build_ai_operations_snapshot,
    build_niche_segmentation,
    build_opportunity_analysis,
    detect_duplicate_groups,
    execute_approved_merge,
    register_not_duplicate,
)
from operia_crm.services.commercial_panel import (
    build_commercial_panel_snapshot,
    prepare_ai_commercial_actions,
    prepare_local_commercial_actions,
)
from operia_crm.services.commercial_workflow import (
    apply_approved_work_package,
    build_leads_operational_view,
)
from operia_crm.services.core import *
from operia_crm.services.emporio_mode import EMPORIO_STATUSES, OPPORTUNITY_TYPES, suggest_emporio_message
from operia_crm.services.import_workflow import (
    SERVER_INBOX_SOURCE,
    UPLOAD_BROWSER_SOURCE,
    build_import_diagnostics,
    build_import_package,
    ensure_import_inbox_dir,
    list_import_inbox_files,
    load_import_inbox_file,
)

st.set_page_config(page_title="OperIA CRM — Empório", layout="wide")
apply_streamlit_auth_guard()
init_db()
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.2rem; padding-bottom: 1.2rem;}
      .stButton > button, .stDownloadButton > button {width: 100%;}
      div[data-testid="stTabs"] [role="tablist"] {
        gap: 0.35rem;
        overflow-x: auto;
        padding-bottom: 0.25rem;
      }
      div[data-testid="stTabs"] [role="tab"] {
        min-width: fit-content;
        padding: 0.45rem 0.7rem;
        white-space: nowrap;
      }
      .commercial-panel-heading {
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 8px;
        background:
          radial-gradient(circle at top left, rgba(20, 184, 166, 0.18), transparent 30%),
          linear-gradient(135deg, #0f172a 0%, #111827 48%, #1f2937 100%);
        box-shadow: 0 18px 44px rgba(2, 6, 23, 0.24);
        color: #f8fafc;
        margin: 0 0 0.85rem;
        padding: 1.05rem 1.1rem;
      }
      .commercial-panel-title {
        color: #f8fafc;
        font-size: 1.58rem;
        font-weight: 700;
        line-height: 1.2;
        margin: 0;
      }
      .commercial-panel-subtitle {
        color: #cbd5e1;
        font-size: 0.96rem;
        font-weight: 600;
        line-height: 1.35;
        margin-top: 0.18rem;
      }
      .commercial-badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.42rem;
        margin-top: 0.8rem;
      }
      .commercial-badge {
        background: rgba(248, 250, 252, 0.1);
        border: 1px solid rgba(203, 213, 225, 0.26);
        border-radius: 999px;
        color: #e2e8f0;
        font-size: 0.78rem;
        font-weight: 700;
        line-height: 1.1;
        padding: 0.36rem 0.58rem;
      }
      .commercial-section-title {
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: 0;
        line-height: 1.25;
        margin: 1.05rem 0 0.35rem;
      }
      .commercial-note {
        color: inherit;
        font-size: 0.92rem;
        line-height: 1.45;
        margin: 0.15rem 0 0.55rem;
        opacity: 0.86;
      }
      .commercial-alert {
        border: 1px solid rgba(251, 191, 36, 0.38);
        border-radius: 8px;
        background: rgba(251, 191, 36, 0.12);
        color: #fef3c7;
        font-size: 0.92rem;
        font-weight: 650;
        line-height: 1.4;
        margin: 0.8rem 0;
        padding: 0.75rem 0.9rem;
      }
      .commercial-kpi-card {
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 8px;
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        box-shadow: 0 12px 30px rgba(2, 6, 23, 0.16);
        color: #f8fafc;
        padding: 0.85rem 0.9rem;
        min-height: 5.6rem;
      }
      .commercial-kpi-label {
        color: #cbd5e1;
        font-size: 0.82rem;
        line-height: 1.25;
        margin-bottom: 0.35rem;
      }
      .commercial-kpi-value {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 750;
        line-height: 1;
      }
      .commercial-action-card {
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 8px;
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.98), rgba(15, 23, 42, 0.98));
        color: #f8fafc;
        padding: 0.82rem 0.9rem;
        margin: 0.45rem 0;
      }
      .commercial-action-contact {
        color: #f8fafc;
        font-size: 0.96rem;
        font-weight: 700;
        line-height: 1.25;
        margin-bottom: 0.25rem;
      }
      .commercial-action-title {
        color: #e2e8f0;
        font-size: 0.9rem;
        line-height: 1.3;
        margin-bottom: 0.2rem;
      }
      .commercial-action-label {
        color: #94a3b8;
        display: inline-block;
        font-size: 0.74rem;
        font-weight: 700;
        line-height: 1.2;
        margin-right: 0.2rem;
        text-transform: uppercase;
      }
      .commercial-action-reason {
        color: #cbd5e1;
        font-size: 0.84rem;
        line-height: 1.35;
      }
      .commercial-action-impact {
        color: #ccfbf1;
        font-size: 0.84rem;
        font-weight: 650;
        line-height: 1.35;
        margin-top: 0.25rem;
      }
      .commercial-suggested-message {
        border-left: 3px solid rgba(20, 184, 166, 0.72);
        color: #dbeafe;
        font-size: 0.84rem;
        line-height: 1.38;
        margin-top: 0.45rem;
        padding-left: 0.55rem;
      }
      .commercial-opportunity-card {
        border: 1px solid rgba(20, 184, 166, 0.28);
        border-radius: 8px;
        background:
          linear-gradient(180deg, rgba(15, 23, 42, 0.99), rgba(17, 24, 39, 0.99));
        box-shadow: 0 16px 38px rgba(2, 6, 23, 0.18);
        color: #f8fafc;
        margin: 0.45rem 0 0.8rem;
        padding: 1rem;
      }
      .commercial-opportunity-grid {
        display: grid;
        gap: 0.55rem;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin: 0.75rem 0;
      }
      .commercial-mini-stat {
        background: rgba(15, 23, 42, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 8px;
        padding: 0.58rem 0.62rem;
      }
      .commercial-mini-label {
        color: #94a3b8;
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1.15;
        text-transform: uppercase;
      }
      .commercial-mini-value {
        color: #f8fafc;
        font-size: 0.9rem;
        font-weight: 700;
        line-height: 1.25;
        margin-top: 0.22rem;
        overflow-wrap: anywhere;
      }
      .commercial-funnel-row {
        align-items: center;
        display: grid;
        gap: 0.55rem;
        grid-template-columns: minmax(8rem, 1fr) minmax(9rem, 4fr) 3rem;
        margin: 0.46rem 0;
      }
      .commercial-funnel-label {
        color: inherit;
        font-size: 0.88rem;
        font-weight: 650;
      }
      .commercial-funnel-track {
        background: rgba(148, 163, 184, 0.16);
        border-radius: 999px;
        height: 0.8rem;
        overflow: hidden;
      }
      .commercial-funnel-fill {
        background: linear-gradient(90deg, #14b8a6, #38bdf8);
        border-radius: 999px;
        height: 100%;
      }
      .commercial-funnel-count {
        color: inherit;
        font-size: 0.88rem;
        font-weight: 750;
        text-align: right;
      }
      .whatsapp-action-button {
        align-items: center;
        background: transparent;
        border: 1px solid rgba(148, 163, 184, 0.35);
        border-radius: 0.5rem;
        color: #f8fafc !important;
        display: flex;
        font-weight: 600;
        justify-content: center;
        min-height: 2.5rem;
        padding: 0.35rem 0.75rem;
        text-align: center;
        text-decoration: none !important;
        width: 100%;
      }
      .whatsapp-action-button:hover {
        border-color: rgba(248, 250, 252, 0.55);
        color: #ffffff !important;
      }
      @media (max-width: 640px) {
        .block-container {padding-left: 0.85rem; padding-right: 0.85rem;}
        div[data-testid="stTabs"] [role="tab"] {
          font-size: 0.86rem;
          padding: 0.38rem 0.55rem;
        }
        .commercial-panel-title {
          font-size: 1.2rem;
        }
        .commercial-panel-heading {
          margin-bottom: 0.65rem;
          padding: 0.7rem 0.75rem;
        }
        .commercial-panel-subtitle {
          font-size: 0.88rem;
        }
        .commercial-section-title {
          font-size: 0.92rem;
          margin-top: 0.85rem;
        }
        .commercial-kpi-card {
          min-height: auto;
          padding: 0.65rem 0.75rem;
        }
        .commercial-kpi-value {
          font-size: 1.55rem;
        }
        .commercial-action-card {
          padding: 0.65rem 0.7rem;
        }
        .commercial-suggested-message {
          font-size: 0.8rem;
        }
        .commercial-opportunity-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .commercial-funnel-row {
          grid-template-columns: 1fr;
          gap: 0.28rem;
        }
        .commercial-funnel-count {
          text-align: left;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("OperIA CRM — Empório")


def commercial_section_title(text: str) -> None:
    st.markdown(f'<div class="commercial-section-title">{escape(text)}</div>', unsafe_allow_html=True)


def commercial_kpi_card(label: str, value: int) -> None:
    st.markdown(
        f"""
        <div class="commercial-kpi-card">
          <div class="commercial-kpi-label">{escape(label)}</div>
          <div class="commercial-kpi-value">{int(value or 0)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def commercial_badges(labels: list[str]) -> None:
    badges = "".join(f'<span class="commercial-badge">{escape(label)}</span>' for label in labels)
    st.markdown(f'<div class="commercial-badge-row">{badges}</div>', unsafe_allow_html=True)


def commercial_alert(text: str) -> None:
    st.markdown(f'<div class="commercial-alert">{escape(text)}</div>', unsafe_allow_html=True)


def commercial_action_card(action: dict) -> None:
    name = escape(str(action.get("lead_name") or "Contato"))
    title = escape(str(action.get("title") or "Ação comercial"))
    weight = escape(str(action.get("weight") or "Médio"))
    state = escape(str(action.get("state") or "aguardando liberação"))
    reason = escape(str(action.get("reason") or "Prioridade comercial do dia."))
    impact = escape(str(action.get("impact") or "Apoia a execução comercial."))
    prepared_content = escape(str(action.get("prepared_content") or action.get("content") or "Registro interno preparado para revisão."))
    suggested_message = str(action.get("suggested_message") or "").strip()
    suggested_html = ""
    if suggested_message:
        suggested_html = f'<div class="commercial-suggested-message">Mensagem preparada para revisão: {escape(suggested_message)}</div>'
    st.markdown(
        f"""
        <div class="commercial-action-card">
          <div class="commercial-action-contact"><span class="commercial-action-label">Contato</span>{name}</div>
          <div class="commercial-action-title"><span class="commercial-action-label">Ação preparada pela IA</span>{title}</div>
          <div class="commercial-action-reason"><span class="commercial-action-label">Peso</span>{weight} <span class="commercial-action-label">Estado</span>{state}</div>
          <div class="commercial-action-reason">Motivo: {reason}</div>
          <div class="commercial-action-impact">Impacto comercial: {impact}</div>
          <div class="commercial-suggested-message">Registro interno preparado: {prepared_content}</div>
          {suggested_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def commercial_temperature(item: dict) -> str:
    if item.get("_emporio_temperature"):
        return str(item.get("_emporio_temperature"))
    score = safe_int(item.get("_score") or item.get("score"))
    status = str(item.get("_stage") or item.get("status") or item.get("status_context") or "").lower()
    has_open_proposal = bool(item.get("_has_open_proposal") or item.get("has_open_proposal"))
    if score >= 85 or has_open_proposal:
        return "🔥 Fervendo"
    if score >= 70 or "negociação" in status or "negociacao" in status:
        return "Quente"
    if score >= 50:
        return "Morno"
    return "Em análise"


def safe_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def action_for_lead(package: dict, lead_id: int) -> dict:
    for action in package.get("prepared_actions") or package.get("day_queue") or []:
        if safe_int(action.get("lead_id")) == safe_int(lead_id):
            return action
    return {}


def lead_by_id(snapshot: dict, lead_id: int) -> dict:
    for item in snapshot.get("lead_facts") or []:
        if safe_int(item.get("_lead_id")) == safe_int(lead_id):
            return item
    return {}


def selected_lead_email(item: dict) -> str:
    return str(item.get("email") or "").strip()


def is_valid_email_for_compose(value: str) -> bool:
    email = str(value or "").strip()
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


def contact_channel(item: dict) -> str:
    if item.get("whatsapp"):
        return "WhatsApp"
    if item.get("phone"):
        return "Telefone"
    if item.get("email"):
        return "E-mail"
    return "Canal a revisar"


def prioritized_opportunities(snapshot: dict, package: dict, limit: int = 5) -> list[dict]:
    facts = list(snapshot.get("lead_facts") or [])

    def sort_key(item: dict) -> tuple[int, int, int]:
        action = action_for_lead(package, safe_int(item.get("_lead_id")))
        duplicate = 1 if item.get("_duplicate_risk") else 0
        hot = 0 if item.get("_has_open_proposal") or item.get("_is_negotiation") or item.get("_is_high_opportunity") else 1
        priority = safe_int(action.get("priority") or 99)
        return (duplicate, hot, priority, -safe_int(item.get("_score")), safe_int(item.get("_lead_id")))

    return sorted(facts, key=sort_key)[: max(1, safe_int(limit))]


def batch_option_label(item: dict, action: dict) -> str:
    lead_id = safe_int(item.get("_lead_id"))
    name = str(item.get("name") or "Contato")
    title = str(action.get("title") or action.get("prepared_content") or "Revisar oportunidade")
    return f"#{lead_id} — {name} | {commercial_temperature(item)} | {title}"


def suggested_email_text(item: dict, action: dict) -> str:
    emporio_message = suggest_emporio_message(item)
    return (
        f"Assunto: Próximos passos Empório\n\n"
        f"{emporio_message}\n\n"
        f"{action.get('prepared_content') or 'Podemos alinhar o próximo passo operacional?'}"
    )


def normalize_phone_for_whatsapp(value: str) -> str:
    digits = re.sub(r"\D+", "", str(value or ""))
    if not digits:
        return ""
    if len(digits) in {10, 11}:
        digits = f"55{digits}"
    if len(digits) < 11 or len(digits) > 15:
        return ""
    return digits


def build_whatsapp_web_url(phone: str, message: str) -> str:
    return f"https://web.whatsapp.com/send?phone={phone}&text={quote(message or '', safe='')}"


def build_whatsapp_app_url(phone: str, message: str) -> str:
    return f"whatsapp://send?phone={phone}&text={quote(message or '', safe='')}"


def build_whatsapp_business_android_intent(phone: str, message: str, fallback_url: str) -> str:
    encoded_phone = quote(phone or "", safe="")
    encoded_message = quote(message or "", safe="")
    encoded_fallback = quote(fallback_url or "", safe="")
    return (
        f"intent://send/?phone={encoded_phone}&text={encoded_message}"
        f"#Intent;scheme=whatsapp;package=com.whatsapp.w4b;S.browser_fallback_url={encoded_fallback};end"
    )


def build_whatsapp_business_android_intent_alt(phone: str, message: str, fallback_url: str) -> str:
    encoded_phone = quote(phone or "", safe="")
    encoded_message = quote(message or "", safe="")
    encoded_fallback = quote(fallback_url or "", safe="")
    return (
        f"intent://send?phone={encoded_phone}&text={encoded_message}"
        f"#Intent;scheme=whatsapp;package=com.whatsapp.w4b;S.browser_fallback_url={encoded_fallback};end"
    )


def parse_email_subject_body(message: str) -> tuple[str, str]:
    text = str(message or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[0].strip().lower().startswith("assunto:"):
        subject = lines[0].split(":", 1)[1].strip() or "Próximos passos"
        body = "\n".join(lines[1:]).lstrip("\n")
        return subject, body
    return "Próximos passos", text


def build_gmail_compose_url(email: str, message: str) -> str:
    subject, body = parse_email_subject_body(message)
    compose_url = (
        "https://mail.google.com/mail/u/0/?view=cm&fs=1&tf=1"
        f"&to={quote(str(email or '').strip(), safe='')}"
        f"&su={quote(subject, safe='')}"
        f"&body={quote(body, safe='')}"
    )
    return f"https://accounts.google.com/AccountChooser?service=mail&continue={quote(compose_url, safe='')}"


def build_mailto_url(email: str, message: str) -> str:
    subject, body = parse_email_subject_body(message)
    return (
        f"mailto:{quote(str(email or '').strip(), safe='')}"
        f"?subject={quote(subject, safe='')}&body={quote(body, safe='')}"
    )


def compose_urls(item: dict, whatsapp_message: str, email_message: str) -> dict[str, str]:
    email = selected_lead_email(item)
    whatsapp_phone = normalize_phone_for_whatsapp(item.get("whatsapp") or item.get("phone") or "")
    whatsapp_web_url = build_whatsapp_web_url(whatsapp_phone, whatsapp_message) if whatsapp_phone else ""
    email_is_valid = is_valid_email_for_compose(email)
    return {
        "whatsapp": build_whatsapp_business_android_intent(whatsapp_phone, whatsapp_message, whatsapp_web_url) if whatsapp_phone else "",
        "whatsapp_alt": build_whatsapp_business_android_intent_alt(whatsapp_phone, whatsapp_message, whatsapp_web_url) if whatsapp_phone else "",
        "whatsapp_app": build_whatsapp_app_url(whatsapp_phone, whatsapp_message) if whatsapp_phone else "",
        "whatsapp_web": whatsapp_web_url,
        "gmail": build_gmail_compose_url(email, email_message) if email_is_valid else "",
        "email_app": build_mailto_url(email, email_message) if email_is_valid else "",
    }


def register_reviewed_channel_action(
    *,
    lead_id: int,
    channel: str,
    message: str,
    followup_days: int,
    package_signature: str,
) -> tuple[bool, str]:
    key = f"{lead_id}:{channel}:{package_signature}:{followup_days}"
    state_key = f"commercial_manual_registration_{key}"
    if st.session_state.get(state_key):
        return False, "Esta ação já foi registrada nesta sessão."
    marker = f"[operia-manual-channel:{key}]"
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM interactions WHERE lead_id = ? AND summary LIKE ? LIMIT 1",
            (lead_id, f"%{marker}%"),
        ).fetchone()
    if existing:
        st.session_state[state_key] = True
        return False, "Esta ação já estava registrada no CRM."
    followup_date = (date.today() + timedelta(days=followup_days)).isoformat()
    summary = (
        f"{marker} Registro manual revisado para {channel}. "
        f"Próximo retorno D+{followup_days}. Conteúdo revisado: {message}"
    )
    interaction_id = register_interaction(lead_id, f"Registro manual {channel}", summary, "manual", followup_date)
    st.session_state[state_key] = True
    return True, f"Interação pendente criada: {interaction_id}"


def render_quick_channel_actions(
    *,
    selected: dict,
    whatsapp_message: str,
    email_message: str,
    package_signature: str,
) -> None:
    lead_id = safe_int(selected.get("_lead_id"))
    urls = compose_urls(selected, whatsapp_message, email_message)
    commercial_section_title("Ações rápidas revisadas por canal")
    st.caption("O app não dispara WhatsApp/e-mail automaticamente. Ele prepara e registra a ação.")
    link_cols = st.columns(4)
    if urls["whatsapp"]:
        with link_cols[0]:
            st.markdown(
                f'<a class="whatsapp-action-button" href="{html_escape(urls["whatsapp"], quote=True)}" target="_self">WhatsApp revisado</a>',
                unsafe_allow_html=True,
            )
        with link_cols[1]:
            st.link_button("WhatsApp Web", urls["whatsapp_web"])
        st.caption("No Android, WhatsApp revisado tenta abrir o WhatsApp Business diretamente. Se o navegador bloquear intents, use WhatsApp Web.")
    else:
        st.warning("Lead sem telefone/WhatsApp válido para abrir conversa.")
    if urls["gmail"]:
        with link_cols[2]:
            st.link_button("Gmail", urls["gmail"])
        with link_cols[3]:
            st.link_button("App e-mail", urls["email_app"])
        st.caption("Gmail Web exige conta Google logada no navegador. Se pedir login, entre e o compose será aberto em seguida.")
    else:
        st.warning("Lead sem e-mail válido para abrir composição.")

    approved = st.checkbox(
        "Revisei o conteúdo e autorizo apenas o registro manual desta ação",
        key=f"panel_channel_manual_approval_{lead_id}_{package_signature}",
    )
    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("Registrar WhatsApp + D+2", key=f"panel_register_whatsapp_{lead_id}_{package_signature}"):
            if not approved:
                st.warning("Marque a aprovação antes de registrar a ação no CRM.")
            else:
                created, message = register_reviewed_channel_action(
                    lead_id=lead_id,
                    channel="WhatsApp",
                    message=whatsapp_message,
                    followup_days=2,
                    package_signature=package_signature,
                )
                st.success(message) if created else st.info(message)
    with action_cols[1]:
        if st.button("Registrar e-mail + D+3", key=f"panel_register_email_{lead_id}_{package_signature}"):
            if not approved:
                st.warning("Marque a aprovação antes de registrar a ação no CRM.")
            else:
                created, message = register_reviewed_channel_action(
                    lead_id=lead_id,
                    channel="e-mail",
                    message=email_message,
                    followup_days=3,
                    package_signature=package_signature,
                )
                st.success(message) if created else st.info(message)
    with action_cols[2]:
        if st.button("Pular por agora", key=f"panel_skip_now_{lead_id}_{package_signature}"):
            st.session_state[f"commercial_panel_skipped_{lead_id}_{package_signature}"] = True
            st.info("Oportunidade mantida sem registro ou alteração crítica.")


def opportunity_table_rows(items: list[dict]) -> list[dict]:
    rows = []
    for item in items:
        rows.append(
            {
                "Contato": item.get("name") or "Contato",
                "Temperatura": commercial_temperature(item),
                "Prioridade": item.get("_emporio_priority") or "Média",
                "Status": item.get("_stage") or item.get("status") or "Em análise",
                "Tipo": item.get("_opportunity_type") or item.get("opportunity_type") or "-",
                "Data": item.get("event_or_delivery_date") or "-",
                "Valor estimado": item.get("estimated_value") or 0,
                "Canal": contact_channel(item),
            }
        )
    return rows


def render_opportunity_card(item: dict, action: dict) -> None:
    name = escape(str(item.get("name") or "Contato"))
    temperature = escape(commercial_temperature(item))
    score = safe_int(item.get("_score") or item.get("score"))
    status = escape(str(item.get("_stage") or item.get("status") or "Em análise"))
    channel = escape(contact_channel(item))
    opportunity_type = escape(str(item.get("_opportunity_type") or item.get("opportunity_type") or "-"))
    event_date = escape(str(item.get("event_or_delivery_date") or "-"))
    estimated_value = escape(str(item.get("estimated_value") or 0))
    reason = escape(str(action.get("reason") or item.get("_duplicate_risk") or "Prioridade comercial identificada na carteira."))
    recommendation = escape(str(action.get("title") or action.get("prepared_content") or "Revisar oportunidade e definir próximo passo."))
    st.markdown(
        f"""
        <div class="commercial-opportunity-card">
          <div class="commercial-action-contact">{name}</div>
          <div class="commercial-opportunity-grid">
            <div class="commercial-mini-stat"><div class="commercial-mini-label">Temperatura</div><div class="commercial-mini-value">{temperature}</div></div>
            <div class="commercial-mini-stat"><div class="commercial-mini-label">Prioridade</div><div class="commercial-mini-value">{escape(str(item.get("_emporio_priority") or score))}</div></div>
            <div class="commercial-mini-stat"><div class="commercial-mini-label">Status</div><div class="commercial-mini-value">{status}</div></div>
            <div class="commercial-mini-stat"><div class="commercial-mini-label">Contato/canal</div><div class="commercial-mini-value">{channel}</div></div>
            <div class="commercial-mini-stat"><div class="commercial-mini-label">Tipo</div><div class="commercial-mini-value">{opportunity_type}</div></div>
            <div class="commercial-mini-stat"><div class="commercial-mini-label">Data</div><div class="commercial-mini-value">{event_date}</div></div>
            <div class="commercial-mini-stat"><div class="commercial-mini-label">Valor estimado</div><div class="commercial-mini-value">{estimated_value}</div></div>
          </div>
          <div class="commercial-action-reason">Motivo: {reason}</div>
          <div class="commercial-action-impact">Ação recomendada: {recommendation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_funnel(snapshot: dict) -> None:
    funnel = snapshot.get("funnel") or {}
    stages = EMPORIO_STATUSES
    max_count = max([safe_int(funnel.get(stage)) for stage in stages] + [1])
    for stage in stages:
        count = safe_int(funnel.get(stage))
        width = max(6, int((count / max_count) * 100)) if count else 0
        st.markdown(
            f"""
            <div class="commercial-funnel-row">
              <div class="commercial-funnel-label">{escape(stage)}</div>
              <div class="commercial-funnel-track"><div class="commercial-funnel-fill" style="width: {width}%;"></div></div>
              <div class="commercial-funnel-count">{count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def unique_commercial_queue(actions: list[dict]) -> list[dict]:
    unique_actions = []
    seen = set()
    for action in actions or []:
        key = (
            str(action.get("lead_id") or action.get("lead_name") or "").strip().lower(),
            str(action.get("type") or "").strip().lower(),
            str(action.get("reason") or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_actions.append(action)
        if len(unique_actions) >= 5:
            break
    return unique_actions


tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Painel Comercial",
    "Leads",
    "Importação",
    "Propostas",
    "Agenda/Histórico",
    "Export/Backup",
    "Central IA",
])

with tab1:
    st.markdown(
        """
        <div class="commercial-panel-heading">
          <h2 class="commercial-panel-title">🧠 OperIA CRM — Empório</h2>
          <div class="commercial-panel-subtitle">Modo operacional para restaurante: retornos, eventos, encomendas, reservas e atendimento corporativo com revisão humana.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    commercial_badges(["Retornos de hoje", "Eventos próximos", "Proposta/cardápio", "IA com revisão"])

    if "commercial_panel_package" not in st.session_state:
        snapshot = build_commercial_panel_snapshot()
        package = prepare_local_commercial_actions(snapshot)
        st.session_state["commercial_panel_snapshot"] = snapshot
        st.session_state["commercial_panel_package"] = package
        st.session_state["commercial_panel_applied_signature"] = ""

    if st.button("Atualizar análise IA da carteira"):
        snapshot = build_commercial_panel_snapshot()
        package = prepare_ai_commercial_actions(snapshot)
        st.session_state["commercial_panel_snapshot"] = snapshot
        st.session_state["commercial_panel_package"] = package

    snapshot = st.session_state.get("commercial_panel_snapshot", {})
    package = st.session_state.get("commercial_panel_package", {})
    package_signature = str(package.get("package_signature") or "empty-operational-package")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        commercial_kpi_card("Oportunidades abertas", int(snapshot.get("total_contatos") or 0) - int(snapshot.get("contatos_fechados") or 0))
    with c2:
        commercial_kpi_card("Retornos pendentes", int(snapshot.get("retornos_a_fazer") or 0))
    with c3:
        commercial_kpi_card("Eventos/entregas próximos", int(snapshot.get("eventos_entregas_proximos") or 0))
    with c4:
        commercial_kpi_card("Propostas/cardápios aguardando retorno", int(snapshot.get("propostas_cardapios_aguardando_retorno") or 0))
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        commercial_kpi_card("Valor estimado em aberto", int(float(snapshot.get("valor_estimado_em_aberto") or 0)))
    with c6:
        commercial_kpi_card("Oportunidades em alta", int(snapshot.get("oportunidades_em_alta") or 0))
    with c7:
        commercial_kpi_card("Contatos parados", int(snapshot.get("contatos_sem_proxima_acao") or 0))
    with c8:
        commercial_kpi_card("Cadastros incompletos", int(snapshot.get("contatos_incompletos") or 0))

    if int(snapshot.get("contatos_com_risco_duplicidade") or 0) > 0:
        commercial_alert("Existem possíveis duplicidades. Revise antes de liberar novas ações comerciais.")

    commercial_section_title("O que o operador deve fazer agora")
    st.write(package.get("main_action") or "Cadastre ou importe contatos para iniciar a análise comercial.")
    st.caption("Nada é enviado ou registrado antes da revisão humana.")

    panel_top5_tab, panel_funnel_tab, panel_review_tab = st.tabs(["Fila operacional", "Funil Empório", "Modo IA com revisão"])

    with panel_top5_tab:
        st.caption("Responde: quem precisa de retorno hoje, quem aguarda proposta/cardápio, quais eventos estão próximos e o que fazer agora.")
        batch_size = st.number_input("Tamanho do lote operacional", min_value=1, max_value=50, value=5, step=1)
        opportunities = prioritized_opportunities(snapshot, package, limit=safe_int(batch_size))
        if opportunities:
            st.dataframe(opportunity_table_rows(opportunities), use_container_width=True, hide_index=True)
            options = [safe_int(item.get("_lead_id")) for item in opportunities]
            labels = {
                safe_int(item.get("_lead_id")): batch_option_label(
                    item,
                    action_for_lead(package, safe_int(item.get("_lead_id"))),
                )
                for item in opportunities
            }
            selected_id = st.selectbox(
                "Lead do lote",
                options=options,
                format_func=lambda lead_id: labels.get(safe_int(lead_id), "Contato"),
            )
            selected = lead_by_id(snapshot, safe_int(selected_id)) or opportunities[0]
            selected_action = action_for_lead(package, safe_int(selected.get("_lead_id")))
            render_opportunity_card(selected, selected_action)
            suggested_message = selected_action.get("suggested_message") or "Mensagem sugerida ainda não preparada. Revise a oportunidade antes de abordar."
            suggested_email = suggested_email_text(selected, selected_action)
            whatsapp_message = st.text_area(
                "Mensagem WhatsApp sugerida para o Empório",
                value=suggested_message,
                height=120,
                key=f"panel_whatsapp_review_{safe_int(selected.get('_lead_id'))}_{package_signature}",
            )
            email_message = st.text_area(
                "E-mail sugerido para o Empório",
                value=suggested_email,
                height=150,
                key=f"panel_email_review_{safe_int(selected.get('_lead_id'))}_{package_signature}",
            )
            render_quick_channel_actions(
                selected=selected,
                whatsapp_message=whatsapp_message,
                email_message=email_message,
                package_signature=package_signature,
            )
        else:
            st.info("Carteira vazia ou sem oportunidade priorizada no momento.")

    with panel_funnel_tab:
        commercial_section_title("Funil operacional Empório")
        render_funnel(snapshot)

    with panel_review_tab:
        st.write("A IA preparou ações internas para revisão.")
        review_actions = unique_commercial_queue(package.get("prepared_actions") or [])[:5]
        if review_actions:
            for action in review_actions:
                commercial_action_card(action)
                st.text_area(
                    "Conteúdo que será registrado",
                    value=str(action.get("prepared_content") or action.get("content") or "Registro interno preparado para revisão."),
                    height=88,
                    key=f"panel_internal_content_{action.get('idempotency_key') or action.get('fingerprint') or action.get('lead_id')}_{package_signature}",
                )
        else:
            st.info("Nenhuma ação interna preparada para este momento.")

        already_applied = st.session_state.get("commercial_panel_applied_signature") == package_signature
        if already_applied:
            st.info("Este pacote já foi registrado. Atualize a análise para revisar um novo pacote.")
        else:
            approved = st.checkbox("Revisei e autorizo apenas o registro interno dessas ações")
            apply_clicked = st.button("Confirmar e registrar no CRM")
            if apply_clicked:
                if not approved:
                    st.warning("Marque a aprovação antes de registrar as ações no CRM.")
                else:
                    created = apply_approved_work_package(package, approved=True)
                    st.session_state["commercial_panel_applied_signature"] = package_signature
                    st.success(f"{created} ações internas registradas no CRM para execução manual.")

    st.markdown(
        "CRM detalhado mantido abaixo em segundo plano. Use apenas para operação detalhada, importação, exportação ou configuração."
    )
    show_legacy_tabs = st.checkbox("Mostrar abas antigas / operação detalhada")
    if show_legacy_tabs:
        with st.container():
            st.write("As abas Leads, Importação, Propostas, Agenda/Histórico, Export/Backup e Central IA continuam disponíveis nesta mesma tela.")
            st.info("O app não dispara WhatsApp/e-mail automaticamente. Ele prepara e registra a ação.")
            st.markdown("**Atalhos operacionais seguros**")
            st.write("Importação CSV inteligente: use a aba Importação para carregar, diagnosticar e confirmar arquivos CSV/XLSX.")
            if st.button("Backup manual do banco", key="panel_manual_backup_shortcut"):
                p = backup_now()
                st.success(f"Backup manual criado: {Path(p).name}")
            if st.button("Inicializar / migrar banco", key="panel_init_db_shortcut"):
                init_db()
                st.success("Inicialização idempotente concluída.")

with tab2:
    st.subheader("Carteira operacional Empório")
    with st.form("lead_form"):
        name = st.text_input("Nome*")
        email = st.text_input("E-mail")
        phone = st.text_input("Telefone")
        status = st.selectbox("Status", ["Novo lead", "Qualificar", "Contato iniciado", "Proposta enviada", "Negociação", "Ganho", "Perdido", "Follow-up futuro"])
        opportunity_type = st.selectbox("Tipo de oportunidade", OPPORTUNITY_TYPES)
        event_or_delivery_date = st.date_input("Data do evento/entrega/reserva", value=None)
        estimated_value = st.number_input("Valor estimado", min_value=0.0, value=0.0, step=50.0)
        people_count = st.number_input("Quantidade de pessoas", min_value=0, value=0, step=1)
        source_channel = st.selectbox("Canal de origem", ["WhatsApp", "Instagram", "Telefone", "Indicação", "Site", "Google", "Presencial", "Cliente antigo", "Outro"])
        emporio_status = st.selectbox("Status Empório", EMPORIO_STATUSES)
        next_action = st.text_input("Próxima ação")
        operational_notes = st.text_area("Observação operacional")
        origin = st.selectbox("Origem", ["Indicação", "WhatsApp", "Instagram", "Site", "Google", "Prospecção ativa", "Evento", "Cliente antigo", "Parceria", "Outro"])
        next_followup = st.date_input("Próximo follow-up", value=None)
        if st.form_submit_button("Salvar") and name:
            create_lead({
                "name": name,
                "email": email,
                "phone": phone,
                "status": status,
                "origin": origin,
                "next_followup": str(next_followup) if next_followup else None,
                "opportunity_type": opportunity_type,
                "event_or_delivery_date": str(event_or_delivery_date) if event_or_delivery_date else None,
                "estimated_value": estimated_value,
                "people_count": people_count,
                "source_channel": source_channel,
                "emporio_status": emporio_status,
                "next_action": next_action,
                "operational_notes": operational_notes,
            })
            st.success("Oportunidade Empório salva")

    operational_rows = build_leads_operational_view()
    display_rows = [{k: v for k, v in row.items() if not k.startswith("_")} for row in operational_rows[:50]]
    if display_rows:
        st.dataframe(display_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum contato cadastrado na carteira.")

    lead_map = {int(row["_lead_id"]): row for row in operational_rows if row.get("_lead_id")}
    if lead_map:
        selected_lead_id = st.selectbox(
            "Contato para revisar",
            options=list(lead_map.keys()),
            format_func=lambda lead_id: f"{lead_id} - {lead_map[lead_id]['Contato']}",
        )
        selected_operational = lead_map[int(selected_lead_id)]
        l = next(dict(row) for row in list_leads() if int(row["id"]) == int(selected_lead_id))
        action = selected_operational.get("_action") or {}
        draft_key = f"lead_internal_draft_{l['id']}"
        duplicate_risk_active = bool(
            selected_operational["Risco de duplicidade"] != "Sem alerta"
            or action.get("type") == "bloquear_acao_duplicada"
            or selected_operational["Próxima ação sugerida"] == "Bloquear ação duplicada"
        )
        st.write(f"Próxima ação sugerida: {selected_operational['Próxima ação sugerida']}")
        st.write(f"Risco de duplicidade: {selected_operational['Risco de duplicidade']}")
        if duplicate_risk_active:
            st.warning("Contato com risco de duplicidade. Revise o cadastro antes de preparar nova ação comercial.")
            if st.button(f"Registrar revisão de duplicidade #{l['id']}", key=f"review_duplicate_{l['id']}"):
                marker = f"[operia-duplicate-review:{l['id']}]"
                with get_conn() as conn:
                    existing = conn.execute(
                        "SELECT id FROM interactions WHERE lead_id = ? AND summary LIKE ? LIMIT 1",
                        (int(l["id"]), f"%{marker}%"),
                    ).fetchone()
                if existing:
                    st.info("Revisão de duplicidade já registrada para este contato.")
                else:
                    summary = f"{marker} Revisar possível duplicidade antes de preparar nova ação comercial."
                    iid = register_interaction(l["id"], "Revisão de duplicidade", summary, "manual")
                    st.info(f"Interação pendente criada: {iid}")
        else:
            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"Preparar abordagem para revisão #{l['id']}", key=f"prepare_approach_{l['id']}"):
                    msg = action.get("suggested_message") or suggest_message(l["name"], "quero entender melhor sua necessidade")
                    st.session_state[draft_key] = {
                        "kind": "Mensagem preparada pela IA",
                        "content": msg,
                    }
            with c2:
                if st.button(f"Preparar próxima ação #{l['id']}", key=f"prepare_next_{l['id']}"):
                    st.session_state[draft_key] = {
                        "kind": "Próxima ação preparada pela IA",
                        "content": action.get("prepared_content") or selected_operational["Próxima ação sugerida"],
                    }
            if st.session_state.get(draft_key):
                prepared = st.session_state[draft_key]
                st.code(prepared.get("content", ""))
                if st.button(f"Registrar mensagem preparada #{l['id']}", key=f"register_prepared_{l['id']}"):
                    iid = register_interaction(l["id"], prepared.get("kind", "Mensagem preparada pela IA"), prepared.get("content", ""), "manual")
                    st.session_state.pop(draft_key, None)
                    st.info(f"Interação pendente criada: {iid}")

with tab3:
    st.header("Importação guiada de CSV/XLSX")
    st.write("Selecione um arquivo, analise o diagnóstico e confirme somente depois de revisar as linhas.")

    workflow_key = "import_workflow_package"
    uploader_key = "import_file_uploader"
    import_mode = st.radio(
        "Escolha como deseja informar o arquivo",
        ["Selecionar no navegador", "Usar arquivo salvo no servidor"],
        horizontal=True,
    )

    if import_mode == "Selecionar no navegador":
        uploaded_file = st.file_uploader(
            "Selecionar arquivo CSV ou XLSX",
            type=["csv", "xlsx"],
            key=uploader_key,
        )
        if uploaded_file is not None:
            content = uploaded_file.getvalue()
            next_package = build_import_package(uploaded_file.name, content, UPLOAD_BROWSER_SOURCE)
            current_package = st.session_state.get(workflow_key)
            if not current_package or current_package.get("sha256") != next_package["sha256"]:
                st.session_state[workflow_key] = next_package
            else:
                st.session_state[workflow_key].update({
                    "file_name": next_package["file_name"],
                    "size": next_package["size"],
                    "file_type": next_package["file_type"],
                    "bytes": content,
                    "source": UPLOAD_BROWSER_SOURCE,
                })
    else:
        inbox_dir = ensure_import_inbox_dir()
        st.write("Coloque o arquivo em imports/inbox e selecione aqui para importar sem depender do seletor do navegador.")
        st.caption(f"Pasta monitorada: {inbox_dir}")
        inbox_files = list_import_inbox_files(inbox_dir)
        if inbox_files:
            selected_inbox_file = st.selectbox("Arquivos encontrados", inbox_files)
            if st.button("Carregar arquivo selecionado"):
                file_name, content = load_import_inbox_file(selected_inbox_file, inbox_dir)
                next_package = build_import_package(file_name, content, SERVER_INBOX_SOURCE)
                current_package = st.session_state.get(workflow_key)
                if not current_package or current_package.get("sha256") != next_package["sha256"]:
                    st.session_state[workflow_key] = next_package
                else:
                    st.session_state[workflow_key].update({
                        "file_name": next_package["file_name"],
                        "size": next_package["size"],
                        "file_type": next_package["file_type"],
                        "bytes": content,
                        "source": SERVER_INBOX_SOURCE,
                    })
        else:
            st.warning("Nenhum CSV/XLSX encontrado em imports/inbox. Coloque o arquivo nessa pasta e atualize a tela.")

    package = st.session_state.get(workflow_key)
    if package is not None:
        if package.get("source") == SERVER_INBOX_SOURCE:
            st.info("Arquivo carregado da pasta do servidor. Revise o diagnóstico antes de importar.")
        else:
            st.info("Arquivo selecionado. Revise o diagnóstico antes de importar.")

    col_analyze, col_clear = st.columns(2)
    with col_analyze:
        analyze_clicked = st.button("Analisar diagnóstico", disabled=package is None or bool(package.get("applied") if package else False))
    with col_clear:
        clear_clicked = st.button("Limpar arquivo selecionado", disabled=package is None)

    if clear_clicked:
        st.session_state.pop(workflow_key, None)
        st.session_state.pop(uploader_key, None)
        st.info("Arquivo removido da sessão. Selecione um arquivo para iniciar uma nova análise.")
        st.stop()

    if analyze_clicked and package is not None:
        if package.get("diagnostics") is None:
            existing = [dict(x) for x in list_leads()]
            diagnostics = build_import_diagnostics(package["file_name"], package["bytes"], existing)
            st.session_state[workflow_key].update({
                "analyzed_at": datetime.now().isoformat(timespec="seconds"),
                "df": diagnostics.get("df"),
                "diagnostics": diagnostics,
                "applied": False,
                "final_summary": None,
            })
        else:
            st.info("Análise já disponível em sessão para este arquivo. Reutilizando o diagnóstico existente.")
        package = st.session_state[workflow_key]

    if package is None:
        st.info("Selecione um CSV ou XLSX para iniciar a importação guiada.")
    else:
        diagnostics = package.get("diagnostics")
        st.markdown("### Arquivo recebido")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Arquivo", package.get("file_name", "-"))
        c2.metric("Tamanho", f"{int(package.get('size') or 0):,} bytes".replace(",", "."))
        c3.metric("Tipo detectado", package.get("file_type", "-"))
        c4.metric("Hash", str(package.get("sha256", ""))[:12] or "-")
        st.caption(f"Origem do arquivo: {package.get('source') or UPLOAD_BROWSER_SOURCE}")
        if package.get("analyzed_at"):
            st.caption(f"Análise registrada em sessão: {package['analyzed_at']}")

        if diagnostics is None:
            st.warning("Arquivo guardado na sessão. Clique em ‘Analisar arquivo’ para validar antes de importar.")
        else:
            if diagnostics.get("success"):
                st.success(diagnostics.get("message"))
            else:
                st.error(diagnostics.get("message"))
            st.write(diagnostics.get("reason"))
            st.write(diagnostics.get("recommendation"))

            st.markdown("### Diagnóstico de leitura")
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Status", "OK" if diagnostics.get("success") else "Falha")
            d2.metric("Linhas", int(diagnostics.get("row_count") or 0))
            d3.metric("Colunas encontradas", len(diagnostics.get("columns") or []))
            d4.metric("Colunas reconhecidas", len(diagnostics.get("recognized_columns") or []))

            st.markdown("**Colunas encontradas**")
            columns = diagnostics.get("columns") or []
            st.write(", ".join(columns) if columns else "Nenhuma coluna identificada.")

            recognized = diagnostics.get("recognized_columns") or []
            st.markdown("**Colunas reconhecidas**")
            if recognized:
                st.dataframe(recognized, use_container_width=True, hide_index=True)
            else:
                st.write("Nenhuma coluna reconhecida.")

            ignored = diagnostics.get("ignored_columns") or []
            st.markdown("**Colunas ignoradas**")
            st.write(", ".join(ignored) if ignored else "Nenhuma coluna ignorada.")

            if diagnostics.get("success"):
                summary = diagnostics.get("summary") or {}
                st.markdown("### Resumo antes da importação")
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Total de linhas", summary.get("total_linhas", 0))
                s2.metric("Prontas para importar", summary.get("prontas_para_importar", 0))
                s3.metric("Duplicadas fortes", summary.get("duplicadas_fortes", 0))
                s4.metric("Duplicadas prováveis", summary.get("duplicadas_provaveis", 0))
                s5, s6, s7, s8 = st.columns(4)
                s5.metric("Ignoradas sem nome", summary.get("ignoradas_sem_nome", 0))
                s6.metric("Ignoradas sem contato", summary.get("ignoradas_sem_contato", 0))
                s7.metric("Com alerta", summary.get("com_alerta", 0))
                s8.metric("Erros", summary.get("erros", 0))

                df = diagnostics.get("df")
                if df is not None:
                    st.markdown("### Prévia do arquivo")
                    st.dataframe(df.head(20), use_container_width=True)

                st.markdown("### Diagnóstico por linha")
                rows = diagnostics.get("rows") or []
                st.dataframe(rows[:200], use_container_width=True, hide_index=True)
                if len(rows) > 200:
                    st.caption(f"Exibindo as primeiras 200 linhas analisadas de {len(rows)}.")

                if package.get("applied"):
                    st.info("Este pacote já foi importado. Para importar novamente, selecione outro arquivo ou clique em ‘Limpar arquivo’.")
                else:
                    if st.button("Confirmar importação"):
                        import_df = df.copy()
                        import_df["dedupe"] = [row.get("dedupe") for row in rows]
                        final_summary = import_deduped_leads(import_df, [dict(x) for x in list_leads()])
                        st.session_state[workflow_key]["applied"] = True
                        st.session_state[workflow_key]["final_summary"] = final_summary
                        st.success("Importação concluída com deduplicação.")

                final_summary = st.session_state.get(workflow_key, {}).get("final_summary")
                if final_summary:
                    st.markdown("### Resumo final da importação")
                    f1, f2, f3 = st.columns(3)
                    f1.metric("Importados", final_summary["importados"])
                    f2.metric("Ignorados por duplicidade", final_summary["ignorados_duplicidade"])
                    f3.metric("Ignorados sem nome", final_summary["ignorados_sem_nome"])
                    f4, f5, f6 = st.columns(3)
                    f4.metric("Ignorados sem contato", final_summary["ignorados_sem_contato"])
                    f5.metric("Erros", final_summary["erros"])
                    f6.metric("Total de linhas", final_summary["total_linhas"])

with tab4:
    leads = [dict(row) for row in list_leads()]
    if leads:
        lead_options = {int(lead["id"]): f"{lead['id']} - {lead['name']}" for lead in leads}
        selected_lead_id = st.selectbox(
            "Lead para proposta",
            options=list(lead_options.keys()),
            format_func=lambda lead_id: lead_options[lead_id],
        )
        selected_lead = next(lead for lead in leads if int(lead["id"]) == int(selected_lead_id))
        total = st.number_input("Valor total", min_value=0.0, value=0.0)
        content = st.text_area("Conteúdo")
        if st.button("IA: melhorar texto da proposta"):
            st.session_state["proposal_ai"] = run_assisted_action("melhorar_proposta", lead=selected_lead, proposal_content=content)
        if st.session_state.get("proposal_ai"):
            ai_result = st.session_state["proposal_ai"]
            st.code(ai_result.get("content", ""))
        if st.button("Criar proposta"):
            number = create_proposal(selected_lead["id"], total, content, None)
            pdf = generate_proposal_pdf(number, selected_lead["name"], total, content)
            st.success(f"Proposta {number} criada. PDF: {pdf}")

with tab5:
    st.subheader("Interações e anexos")
    leads = [dict(row) for row in list_leads()]
    if leads:
        lead_options = {int(lead["id"]): lead["name"] for lead in leads}
        selected_lead_id = st.selectbox(
            "Lead",
            options=list(lead_options.keys()),
            key="lead_hist",
            format_func=lambda lead_id: lead_options[lead_id],
        )
        up = st.file_uploader("Anexo seguro", key="att")
        if up and st.button("Salvar anexo"):
            save_attachment(selected_lead_id, up.name, up.getvalue())
            st.success("Anexo salvo")

        st.markdown("#### Interações (pendente/confirmada manualmente)")
        interactions = list_interactions(selected_lead_id)
        h1, h2 = st.columns(2)
        with h1:
            if st.button("IA: resumir histórico"):
                st.session_state["hist_ai"] = run_assisted_action("resumir_historico", lead=next(x for x in leads if int(x["id"])==int(selected_lead_id)), interactions=[dict(i) for i in interactions])
        with h2:
            if st.button("IA: sugerir follow-up"):
                st.session_state["hist_ai"] = run_assisted_action("proxima_acao", lead=next(x for x in leads if int(x["id"])==int(selected_lead_id)), interactions=[dict(i) for i in interactions])
        if st.session_state.get("hist_ai"):
            ai_result = st.session_state["hist_ai"]
            st.code(ai_result.get("content", ""))
            if st.button("Registrar sugestão IA como pendente"):
                iid = register_interaction(selected_lead_id, "Sugestão IA", ai_result.get("content", ""), "manual")
                st.success(f"Interação pendente criada: {iid}")
        for it in interactions[:20]:
            status = "Pendente" if it["pending"] else "Confirmada"
            st.write(f"#{it['id']} | {it['kind']} | {status} | {it['summary']}")
            if it["pending"] and st.button(f"Confirmar manualmente #{it['id']}", key=f"confirm_{it['id']}"):
                confirm_interaction(it["id"])
                st.success("Interação confirmada manualmente")

with tab6:
    st.download_button("Exportar CSV", export_leads_csv(), file_name="leads.csv")
    if st.button("Gerar backup local"):
        p = backup_now()
        rel_path = Path(p)
        st.success(f"Backup criado: {rel_path.resolve()} (relativo: {rel_path})")
        st.download_button(
            "Download do backup .db",
            data=Path(p).read_bytes(),
            file_name=Path(p).name,
            mime="application/x-sqlite3",
        )

with tab7:
    st.header("Central IA")
    st.write("A IA analisa, prepara e recomenda. O operador aprova a execução.")

    if "central_ia_snapshot" not in st.session_state:
        st.session_state["central_ia_snapshot"] = build_ai_operations_snapshot()
        st.session_state["central_ia_duplicates"] = detect_duplicate_groups(st.session_state["central_ia_snapshot"])
        st.session_state["central_ia_opportunities"] = build_opportunity_analysis(st.session_state["central_ia_snapshot"])
        st.session_state["central_ia_niches"] = build_niche_segmentation(st.session_state["central_ia_snapshot"])

    if st.button("Atualizar análise da Central IA"):
        st.session_state["central_ia_snapshot"] = build_ai_operations_snapshot()
        st.session_state["central_ia_duplicates"] = detect_duplicate_groups(st.session_state["central_ia_snapshot"])
        st.session_state["central_ia_opportunities"] = build_opportunity_analysis(st.session_state["central_ia_snapshot"])
        st.session_state["central_ia_niches"] = build_niche_segmentation(st.session_state["central_ia_snapshot"])

    duplicate_groups = st.session_state.get("central_ia_duplicates") or []
    opportunities = st.session_state.get("central_ia_opportunities") or []
    niches = st.session_state.get("central_ia_niches") or {"summary": [], "rows": []}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Duplicidades encontradas", len(duplicate_groups))
    c2.metric("Oportunidades quentes", sum(1 for item in opportunities if item.get("temperature") == "Quente"))
    c3.metric("Nichos prioritários", sum(1 for item in niches.get("summary", []) if item.get("priority") == "Alta"))
    c4.metric("Ações aguardando aprovação", len(duplicate_groups) + min(len(opportunities), 5) + min(len(niches.get("summary", [])), 5))

    central_tab1, central_tab2, central_tab3 = st.tabs([
        "Deduplicação IA",
        "Análise de oportunidades",
        "Segmentação por nicho e score",
    ])

    with central_tab1:
        st.subheader("Deduplicação IA")
        if not duplicate_groups:
            st.info("Nenhum grupo de duplicidade identificado neste momento.")
        for index, group in enumerate(duplicate_groups[:5], start=1):
            plan = group.get("merge_plan") or {}
            st.markdown(f"### Grupo de duplicidade #{index}")
            st.write(f"Confiança: {group.get('confidence')}")
            st.write(f"Motivo: {group.get('reason')}")
            st.write(f"Principal sugerido: #{plan.get('principal_id')} {plan.get('principal_name')}")
            duplicate_labels = []
            for lead in group.get("leads") or []:
                if int(lead.get("id") or 0) in set(plan.get("duplicate_ids") or []):
                    duplicate_labels.append(f"#{lead.get('id')} {lead.get('name')}")
            st.write("Possíveis duplicados: " + (", ".join(duplicate_labels) if duplicate_labels else "-"))
            comparison_rows = [
                {
                    "Campo": item.get("field"),
                    "Principal sugerido": item.get("principal"),
                    "Duplicado": item.get("duplicates"),
                    "Ação sugerida": item.get("suggested_action"),
                }
                for item in plan.get("comparisons", [])[:10]
            ]
            st.dataframe(comparison_rows, use_container_width=True, hide_index=True)
            st.write(f"Risco operacional: {plan.get('risk')}")
            confirm_key = f"central_merge_confirm_{plan.get('idempotency_key')}"
            approved = st.checkbox("Confirmo que revisei o plano de merge e autorizo a execução.", key=confirm_key)
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button(f"Preparar plano de deduplicação #{index}", key=f"central_prepare_merge_{plan.get('idempotency_key')}"):
                    st.info("Plano preparado para revisão do operador.")
            with col_b:
                if st.button(f"Executar merge aprovado #{index}", key=f"central_execute_merge_{plan.get('idempotency_key')}"):
                    result = execute_approved_merge(plan, approved=approved)
                    st.info(result.get("message"))
                    if result.get("applied"):
                        st.session_state["central_ia_snapshot"] = build_ai_operations_snapshot()
                        st.session_state["central_ia_duplicates"] = detect_duplicate_groups(st.session_state["central_ia_snapshot"])
                        st.session_state["central_ia_opportunities"] = build_opportunity_analysis(st.session_state["central_ia_snapshot"])
                        st.session_state["central_ia_niches"] = build_niche_segmentation(st.session_state["central_ia_snapshot"])
            with col_c:
                if st.button(f"Registrar como não duplicado #{index}", key=f"central_not_duplicate_{group.get('group_id')}"):
                    result = register_not_duplicate(group, approved=True)
                    st.info(result.get("message"))
            if st.button(f"Ignorar por enquanto #{index}", key=f"central_ignore_duplicate_{group.get('group_id')}"):
                st.info("Grupo mantido sem execução neste momento.")

    with central_tab2:
        st.subheader("Análise de oportunidades")
        if not opportunities:
            st.info("Nenhuma oportunidade identificada neste momento.")
        for item in opportunities[:10]:
            st.markdown(f"### {item.get('lead_name')}")
            oc1, oc2, oc3, oc4 = st.columns(4)
            oc1.metric("Score IA", int(item.get("score") or 0))
            oc2.metric("Temperatura", item.get("temperature") or "-")
            oc3.metric("Prioridade", item.get("priority") or "-")
            oc4.metric("Confiança", item.get("confidence") or "-")
            st.write(f"Motivo: {item.get('reason')}")
            st.write(f"Próxima melhor ação: {item.get('next_best_action')}")
            st.write(f"Impacto comercial: {item.get('impact')}")
            st.write("Mensagem preparada para revisão")
            st.write(item.get("suggested_message") or "Sem mensagem preparada.")
            approved = st.checkbox("Aprovo registrar esta análise no CRM.", key=f"central_opportunity_approve_{item.get('idempotency_key')}")
            if st.button(f"Aplicar análise IA no CRM #{item.get('lead_id')}", key=f"central_apply_opportunity_{item.get('idempotency_key')}"):
                result = apply_approved_opportunity_record(item, approved=approved)
                st.info(result.get("message"))

    with central_tab3:
        st.subheader("Segmentação por nicho e score")
        summary_rows = [
            {
                "Nicho": item.get("niche"),
                "Leads": item.get("total"),
                "Score médio": item.get("average_score"),
                "Quentes": item.get("hot"),
                "Mornos": item.get("warm"),
                "Frios": item.get("cold"),
                "Prioridade": item.get("priority"),
                "Ação recomendada": item.get("recommended_action"),
            }
            for item in niches.get("summary", [])
        ]
        if summary_rows:
            st.dataframe(summary_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum nicho identificado neste momento.")

        for item in (niches.get("summary") or [])[:5]:
            st.markdown(f"### {item.get('niche')}")
            st.write(f"Ação recomendada: {item.get('recommended_action')}")
            approved = st.checkbox("Aprovo registrar esta análise de nicho no CRM.", key=f"central_niche_approve_{item.get('niche')}")
            if st.button(f"Registrar análise de nicho no CRM - {item.get('niche')}", key=f"central_apply_niche_{item.get('niche')}"):
                result = apply_approved_niche_record(item, approved=approved)
                st.info(result.get("message"))
