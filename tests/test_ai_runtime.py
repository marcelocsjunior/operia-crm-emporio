import os

from operia_crm.ai.assistant import suggest_message
from operia_crm.ai.runtime import build_context, run_assisted_action


def test_fallback_without_active_provider(monkeypatch):
    monkeypatch.setattr("operia_crm.ai.runtime.list_ai_models", lambda active=True: [])
    res = run_assisted_action("analisar_lead", lead={"name": "A", "score": 80, "status": "Negociação"})
    assert res["used_fallback"] is True
    assert res["content"]
    assert res["action"] == "analisar_lead"


def test_priority_order(monkeypatch):
    order = []
    models = [
        {"provider_name": "Ollama", "model_name": "m1", "priority": 2, "base_url": "http://x"},
        {"provider_name": "Gemini", "model_name": "m2", "priority": 1, "provider_ref": "NO_KEY"},
    ]
    monkeypatch.setattr("operia_crm.ai.runtime.list_ai_models", lambda active=True: models)

    def fake_ollama(model, prompt):
        order.append(model["model_name"])
        return "ok"

    def fake_gemini(model, prompt):
        order.append(model["model_name"])
        raise RuntimeError("no key")

    monkeypatch.setattr("operia_crm.ai.runtime._call_ollama", fake_ollama)
    monkeypatch.setattr("operia_crm.ai.runtime._call_gemini", fake_gemini)
    run_assisted_action("proxima_acao", lead={"name": "A"})
    assert order == ["m2", "m1"]


def test_ollama_payload_mock(monkeypatch):
    captured = {}

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return b"{\"response\": \"done\"}"

    def fake_urlopen(req, timeout):
        import json as _json
        captured["url"] = req.full_url
        captured["json"] = _json.loads(req.data.decode())
        captured["timeout"] = timeout
        return R()

    monkeypatch.setattr("operia_crm.ai.runtime.request.urlopen", fake_urlopen)
    from operia_crm.ai.runtime import _call_ollama

    out = _call_ollama({"base_url": "http://localhost:11434", "model_name": "qwen"}, "p")
    assert out == "done"
    assert captured["json"]["stream"] is False


def test_api_missing_env_no_secret_leak(monkeypatch):
    monkeypatch.setattr("operia_crm.ai.runtime.list_ai_models", lambda active=True: [{"provider_name": "Gemini", "model_name": "gem", "priority": 1, "provider_ref": "MY_SECRET_KEY"}])
    monkeypatch.delenv("MY_SECRET_KEY", raising=False)
    res = run_assisted_action("email", lead={"name": "A"})
    assert res["used_fallback"] is True
    assert "MY_SECRET_KEY" not in (res.get("error") or "")


def test_context_builder():
    ctx = build_context("analisar_lead", lead={"status": "Novo lead", "score": 55, "name": "Lead"}, interactions=[{"summary": "oi"}])
    assert "status=Novo lead" in ctx
    assert "score=55" in ctx
    assert "Interações" in ctx


def test_suggest_message_compatibility():
    msg = suggest_message("Maria", "vi sua solicitação")
    assert "Maria" in msg
