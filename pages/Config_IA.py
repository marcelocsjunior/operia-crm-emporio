import pandas as pd
import streamlit as st

from operia_crm.auth import apply_streamlit_auth_guard
from operia_crm.database.db import init_db
from operia_crm.services.ai_config import (
    PROVIDER_OPTIONS,
    PROVIDER_TYPES,
    create_ai_model,
    get_ai_settings,
    list_ai_models,
    mask_secret_reference,
    restore_default_ai_prompt,
    run_ai_model_config_test,
    save_ai_model_priorities,
    set_ai_model_active,
    update_ai_model,
    update_ai_settings,
)

st.set_page_config(page_title="Config IA — OperIA CRM Empório", layout="wide")
apply_streamlit_auth_guard()
init_db()
st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 1.2rem;}
.stButton > button, .stDownloadButton > button {width: 100%;}
</style>
""", unsafe_allow_html=True)

st.title("Configurações de IA")
st.caption("Modelos locais/gratuitos, prompt editável, referências externas mascaradas e prioridade automática.")

tab_commercial, tab_active, tab_inactive, tab_editor = st.tabs([
    "Comercial", "Modelos ativos", "Modelos inativos", "Adicionar/editar modelo"
])


def _models_dataframe(models: list[dict]) -> pd.DataFrame:
    rows = []
    for model in models:
        rows.append({
            "id": model["id"],
            "provider_name": model["provider_name"],
            "provider_type": model["provider_type"],
            "model_name": model["model_name"],
            "base_url": model.get("base_url") or "-",
            "priority": model["priority"],
            "last_test_at": model.get("last_test_at") or "-",
            "last_test_status": model.get("last_test_status") or "-",
        })
    return pd.DataFrame(rows)


def _model_header(model: dict) -> str:
    return f"#{model['id']} - {model['provider_name']} / {model['model_name']}"


def _render_model_card(model: dict, active_view: bool) -> tuple[int, int]:
    with st.expander(_model_header(model), expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.write(f"Tipo: {model['provider_type']}")
        c2.write(f"Prioridade: {model['priority']}")
        c3.write(f"Último teste: {model.get('last_test_at') or '-'}")
        st.write(f"Base URL: `{model.get('base_url') or '-'}`")
        st.write(f"Referência externa: {mask_secret_reference(model.get('provider_ref'))}")
        st.write(f"Resultado: {model.get('last_test_status') or '-'}")
        if model.get("last_test_message"):
            st.caption(model["last_test_message"])
        new_priority = st.number_input(
            "Nova prioridade",
            min_value=1,
            max_value=99,
            value=int(model["priority"]),
            key=f"priority_{model['id']}_{active_view}",
        )
        test_message = st.text_area(
            "Mensagem teste personalizada",
            value="",
            placeholder="Opcional. Se vazio, usa teste rápido.",
            key=f"test_msg_{model['id']}_{active_view}",
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Testar modelo", key=f"test_{model['id']}_{active_view}"):
                result = run_ai_model_config_test(model["id"], test_message)
                if result["status"] == "Sucesso":
                    st.success(result["message"])
                elif result["status"] == "Pendente":
                    st.warning(result["message"])
                else:
                    st.error(result["message"])
                st.rerun()
        with b2:
            action_label = "Desativar modelo" if active_view else "Reativar modelo"
            if st.button(action_label, key=f"toggle_{model['id']}_{active_view}"):
                set_ai_model_active(model["id"], not active_view)
                st.success("Status do modelo atualizado")
                st.rerun()
        return int(model["id"]), int(new_priority)


with tab_commercial:
    current = get_ai_settings()
    with st.form("ai_commercial_form"):
        commercial_name = st.text_input("Nome comercial usado nas mensagens", value=current.get("commercial_name") or "OperIA CRM — Empório")
        commercial_description = st.text_area("Descrição comercial padrão", value=current.get("commercial_description") or "", height=110)
        communication_tone = st.text_area("Tom de comunicação", value=current.get("communication_tone") or "", height=90)
        auto_priority = st.checkbox("Modo automático por prioridade", value=bool(current.get("auto_priority")))
        prompt_template = st.text_area("Prompt padrão interno", value=current.get("prompt_template") or "", height=270)
        c1, c2 = st.columns(2)
        save = c1.form_submit_button("Salvar configurações")
        restore = c2.form_submit_button("Restaurar prompt padrão")
    if save:
        update_ai_settings(commercial_name, commercial_description, communication_tone, auto_priority, prompt_template)
        st.success("Configurações de IA salvas")
        st.rerun()
    if restore:
        restore_default_ai_prompt()
        st.success("Prompt padrão restaurado")
        st.rerun()
    st.caption(f"Última alteração do prompt: {current.get('updated_at') or '-'}")

with tab_active:
    active_models = list_ai_models(active=True)
    st.subheader("Modelos ativos")
    if active_models:
        st.dataframe(_models_dataframe(active_models), use_container_width=True, hide_index=True)
        priority_updates = {}
        for model in active_models:
            model_id, priority = _render_model_card(model, active_view=True)
            priority_updates[model_id] = priority
        if st.button("Salvar ordem de prioridade", key="save_active_priorities"):
            save_ai_model_priorities(priority_updates)
            st.success("Ordem de prioridade salva")
            st.rerun()
    else:
        st.info("Nenhum modelo ativo.")

with tab_inactive:
    inactive_models = list_ai_models(active=False)
    st.subheader("Modelos inativos")
    if inactive_models:
        st.dataframe(_models_dataframe(inactive_models), use_container_width=True, hide_index=True)
        priority_updates = {}
        for model in inactive_models:
            model_id, priority = _render_model_card(model, active_view=False)
            priority_updates[model_id] = priority
        if st.button("Salvar prioridades dos inativos", key="save_inactive_priorities"):
            save_ai_model_priorities(priority_updates)
            st.success("Prioridades salvas")
            st.rerun()
    else:
        st.info("Nenhum modelo inativo.")

with tab_editor:
    st.subheader("Adicionar modelo")
    with st.form("add_ai_model_form"):
        provider_name = st.selectbox("Provedor", PROVIDER_OPTIONS, index=0)
        provider_type = st.selectbox("Tipo", PROVIDER_TYPES, index=0)
        base_url = st.text_input("Base URL / endpoint", value="http://localhost:11434")
        model_name = st.text_input("Nome do modelo", value="qwen2.5:1.5b")
        external_ref = st.text_input("Referência externa", value="", help="Informe só o nome da variável local. Não cole valor sensível aqui.")
        active = st.checkbox("Ativo", value=True)
        add = st.form_submit_button("Adicionar modelo")
    if add:
        try:
            create_ai_model(provider_name, provider_type, model_name, base_url, external_ref, active)
            st.success("Modelo adicionado")
            st.rerun()
        except Exception as exc:
            st.error(f"Falha ao adicionar modelo: {exc}")
    st.divider()
    st.subheader("Editar modelo existente")
    all_models = list_ai_models(active=None)
    if all_models:
        options = {int(model["id"]): _model_header(model) for model in all_models}
        selected_id = st.selectbox("Modelo", options=list(options.keys()), format_func=lambda model_id: options[model_id])
        selected = next(model for model in all_models if int(model["id"]) == int(selected_id))
        provider_index = PROVIDER_OPTIONS.index(selected["provider_name"]) if selected["provider_name"] in PROVIDER_OPTIONS else len(PROVIDER_OPTIONS) - 1
        type_index = PROVIDER_TYPES.index(selected["provider_type"]) if selected["provider_type"] in PROVIDER_TYPES else 0
        with st.form("edit_ai_model_form"):
            edit_provider = st.selectbox("Provedor", PROVIDER_OPTIONS, index=provider_index, key="edit_provider")
            edit_type = st.selectbox("Tipo", PROVIDER_TYPES, index=type_index, key="edit_type")
            edit_base_url = st.text_input("Base URL / endpoint", value=selected.get("base_url") or "")
            edit_model_name = st.text_input("Nome do modelo", value=selected.get("model_name") or "")
            edit_external_ref = st.text_input("Referência externa", value=selected.get("provider_ref") or "")
            edit_active = st.checkbox("Ativo", value=bool(selected.get("active")))
            edit_priority = st.number_input("Prioridade", min_value=1, max_value=99, value=int(selected.get("priority") or 99))
            update = st.form_submit_button("Atualizar modelo")
        if update:
            try:
                update_ai_model(selected_id, edit_provider, edit_type, edit_model_name, edit_base_url, edit_external_ref, edit_active, edit_priority)
                st.success("Modelo atualizado")
                st.rerun()
            except Exception as exc:
                st.error(f"Falha ao atualizar modelo: {exc}")
    else:
        st.info("Nenhum modelo cadastrado.")
