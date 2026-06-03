from __future__ import annotations

import os
from typing import Any

import json
from urllib import request, error

from operia_crm.services.ai_config import get_ai_settings, list_ai_models

LOCAL_TIMEOUT_SECONDS = 3
EXTERNAL_TIMEOUT_SECONDS = 30


def build_context(action: str, lead: dict[str, Any] | None = None, interactions: list[dict[str, Any]] | None = None, proposal_content: str | None = None) -> str:
    settings = get_ai_settings()
    lead = lead or {}
    interactions = interactions or []
    return (
        f"Ação: {action}\n"
        f"Prompt: {settings.get('prompt_template', '')}\n"
        f"Nome comercial: {settings.get('commercial_name', '')}\n"
        f"Descrição comercial: {settings.get('commercial_description', '')}\n"
        f"Tom: {settings.get('communication_tone', '')}\n"
        f"Lead: nome={lead.get('name','-')} status={lead.get('status','-')} origem={lead.get('origin','-')} score={lead.get('score','-')} cidade={lead.get('city','-')} segmento={lead.get('segment','-')} notas={lead.get('notes','-')}\n"
        f"Interações: {interactions[:5]}\n"
        f"Proposta atual: {proposal_content or '-'}"
    )


def _normalized(success: bool, provider_name: str, model_name: str, source: str, action: str, content: str, error: str | None, used_fallback: bool) -> dict[str, Any]:
    return {
        "success": success,
        "provider_name": provider_name,
        "model_name": model_name,
        "source": source,
        "action": action,
        "content": content,
        "error": error,
        "used_fallback": used_fallback,
    }


def _safe_error(prefix: str, exc: Exception) -> str:
    text = str(exc)
    text = text[:160]
    return f"{prefix}: {text}"


def _call_ollama(model: dict[str, Any], prompt: str) -> str:
    url = f"{(model.get('base_url') or 'http://localhost:11434').rstrip('/')}/api/generate"
    payload = {"model": model.get("model_name"), "prompt": prompt, "stream": False}
    req = request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=LOCAL_TIMEOUT_SECONDS) as res:
        data = json.loads(res.read().decode())
    return data.get("response", "").strip()


def _call_gemini(model: dict[str, Any], prompt: str) -> str:
    env_name = (model.get("provider_ref") or "").strip() or "GEMINI_API_KEY"
    key = os.getenv(env_name, "")
    if not key:
        raise RuntimeError("Gemini sem chave configurada")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model.get('model_name')}:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    req = request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=EXTERNAL_TIMEOUT_SECONDS) as res:
        data = json.loads(res.read().decode())
    return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()


def _call_cloudflare(model: dict[str, Any], prompt: str) -> str:
    base_url = (model.get("base_url") or "").strip()
    env_name = (model.get("provider_ref") or "").strip()
    if not base_url or not env_name:
        raise RuntimeError("Cloudflare requer base_url e provider_ref")
    token = os.getenv(env_name, "")
    if not token:
        raise RuntimeError("Cloudflare sem token configurado")
    req = request.Request(base_url, data=json.dumps({"prompt": prompt}).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with request.urlopen(req, timeout=EXTERNAL_TIMEOUT_SECONDS) as res:
        data = json.loads(res.read().decode())
    return (data.get("result") or {}).get("response", "").strip()


def _call_vultr(model: dict[str, Any], prompt: str) -> str:
    base_url = (model.get("base_url") or "").strip()
    provider_ref = (model.get("provider_ref") or "").strip()
    model_name = (model.get("model_name") or "").strip()
    if not base_url:
        raise RuntimeError("Vultr requer base_url")
    if not provider_ref or not os.getenv(provider_ref, ""):
        raise RuntimeError("Vultr sem chave configurada")
    if not model_name:
        raise RuntimeError("Nome do modelo não configurado")

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "stream": False,
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {os.getenv(provider_ref, '')}",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req, timeout=EXTERNAL_TIMEOUT_SECONDS) as res:
        data = json.loads(res.read().decode())
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("Resposta vazia do Vultr")
    return content


def _fallback(action: str, lead: dict[str, Any] | None) -> str:
    lead = lead or {}
    status = (lead.get("status") or "").lower()
    score = int(lead.get("score") or 0)
    has_contact = bool((lead.get("phone") or lead.get("whatsapp") or lead.get("email")))
    temp = "quente" if score >= 70 else "morno"
    if action == "analisar_lead":
        reason = "etapa de negociação" if status in {"proposta enviada", "negociação"} else "lead em evolução"
        return f"Resumo: lead {lead.get('name','-')} com temperatura {temp}. Motivo: {reason}. Próxima ação: follow-up consultivo."
    if action == "proxima_acao":
        return "Ação recomendada: follow-up comercial. Prioridade: alta." if status in {"proposta enviada", "negociação"} else "Ação recomendada: abordagem inicial. Prioridade: média."
    if action == "whatsapp":
        return "Olá! Podemos avançar com sua demanda?"
    if action == "email":
        return "Assunto: Próximos passos\n\nOlá, seguem próximos passos para evoluirmos."
    if action == "resumir_historico":
        if not has_contact:
            return "Sem contato válido. Pendência: enriquecer dados. Próxima ação: corrigir telefone/e-mail."
        return "Último contato registrado. Próxima ação: confirmar interesse e data de retorno."
    if action == "melhorar_proposta":
        return "Escopo sugerido: diagnóstico, implementação e acompanhamento. Observações: manter valor sob revisão humana."
    if action == "painel_comercial":
        return "Painel comercial preparado com foco em prioridades internas e revisão humana."
    return "Sugestão assistiva gerada localmente."


def run_assisted_action(action: str, lead: dict[str, Any] | None = None, interactions: list[dict[str, Any]] | None = None, proposal_content: str | None = None) -> dict[str, Any]:
    prompt = build_context(action, lead, interactions, proposal_content)
    models = list_ai_models(active=True)
    errors: list[str] = []
    for model in sorted(models, key=lambda m: int(m.get("priority") or 99)):
        provider = (model.get("provider_name") or "").lower()
        try:
            if provider == "ollama":
                content = _call_ollama(model, prompt)
            elif provider == "gemini":
                content = _call_gemini(model, prompt)
            elif provider == "cloudflare":
                content = _call_cloudflare(model, prompt)
            elif provider == "vultr":
                content = _call_vultr(model, prompt)
            else:
                continue
            if content:
                return _normalized(True, model.get("provider_name", "-"), model.get("model_name", "-"), "provider", action, content, None, False)
        except Exception as exc:  # noqa: BLE001
            errors.append(_safe_error(model.get("provider_name", "provider"), exc))
    content = _fallback(action, lead)
    return _normalized(True, "fallback_local", "deterministic_rules", "fallback", action, content, "; ".join(errors) if errors else None, True)
