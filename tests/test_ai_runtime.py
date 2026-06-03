import os

from operia_crm.ai.assistant import suggest_message
from operia_crm.ai.runtime import build_context, run_assisted_action
from operia_crm.services.ai_config import PROVIDER_OPTIONS


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


def test_provider_options_include_vultr_and_preserve_existing_providers():
    assert PROVIDER_OPTIONS == ("Ollama", "Gemini", "Cloudflare", "Vultr", "Outro")


def test_vultr_provider_recognized(monkeypatch):
    models = [{"provider_name": "Vultr", "model_name": "vultr-model", "priority": 1}]
    monkeypatch.setattr("operia_crm.ai.runtime.list_ai_models", lambda active=True: models)
    monkeypatch.setattr("operia_crm.ai.runtime._call_vultr", lambda model, prompt: "vultr ok")

    res = run_assisted_action("proxima_acao", lead={"name": "A"})

    assert res["used_fallback"] is False
    assert res["provider_name"] == "Vultr"
    assert res["content"] == "vultr ok"


def test_vultr_payload_headers_and_response_mock(monkeypatch):
    captured = {}

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return b"{\"choices\": [{\"message\": {\"content\": \"vultr response\"}}]}"

    def fake_urlopen(req, timeout):
        import json as _json
        captured["url"] = req.full_url
        captured["json"] = _json.loads(req.data.decode())
        captured["headers"] = dict(req.header_items())
        captured["timeout"] = timeout
        return R()

    monkeypatch.setenv("VULTR_INFERENCE_API_KEY", "fake-vultr-key")
    monkeypatch.setattr("operia_crm.ai.runtime.request.urlopen", fake_urlopen)
    from operia_crm.ai.runtime import EXTERNAL_TIMEOUT_SECONDS, _call_vultr

    out = _call_vultr(
        {
            "base_url": "https://api.vultrinference.com/v1/",
            "model_name": "vultr-chat",
            "provider_ref": "VULTR_INFERENCE_API_KEY",
        },
        "hello",
    )

    assert out == "vultr response"
    assert captured["url"] == "https://api.vultrinference.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer fake-vultr-key"
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["json"]["model"] == "vultr-chat"
    assert captured["json"]["messages"] == [{"role": "user", "content": "hello"}]
    assert captured["json"]["temperature"] == 0.3
    assert captured["json"]["stream"] is False
    assert captured["timeout"] == EXTERNAL_TIMEOUT_SECONDS


def test_vultr_missing_key_controlled_error(monkeypatch):
    monkeypatch.delenv("VULTR_INFERENCE_API_KEY", raising=False)
    from operia_crm.ai.runtime import _call_vultr

    try:
        _call_vultr(
            {
                "base_url": "https://api.vultrinference.com/v1",
                "model_name": "vultr-chat",
                "provider_ref": "VULTR_INFERENCE_API_KEY",
            },
            "hello",
        )
    except RuntimeError as exc:
        assert str(exc) == "Vultr sem chave configurada"
    else:
        raise AssertionError("expected RuntimeError")


def test_vultr_missing_base_url_controlled_error(monkeypatch):
    monkeypatch.setenv("VULTR_INFERENCE_API_KEY", "fake-vultr-key")
    from operia_crm.ai.runtime import _call_vultr

    try:
        _call_vultr(
            {"base_url": "", "model_name": "vultr-chat", "provider_ref": "VULTR_INFERENCE_API_KEY"},
            "hello",
        )
    except RuntimeError as exc:
        assert str(exc) == "Vultr requer base_url"
    else:
        raise AssertionError("expected RuntimeError")


def test_vultr_missing_model_name_controlled_error(monkeypatch):
    monkeypatch.setenv("VULTR_INFERENCE_API_KEY", "fake-vultr-key")
    from operia_crm.ai.runtime import _call_vultr

    try:
        _call_vultr(
            {
                "base_url": "https://api.vultrinference.com/v1",
                "model_name": "",
                "provider_ref": "VULTR_INFERENCE_API_KEY",
            },
            "hello",
        )
    except RuntimeError as exc:
        assert str(exc) == "Nome do modelo não configurado"
    else:
        raise AssertionError("expected RuntimeError")


def test_vultr_empty_response_controlled_error(monkeypatch):
    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return b"{\"choices\": [{\"message\": {\"content\": \"\"}}]}"

    monkeypatch.setenv("VULTR_INFERENCE_API_KEY", "fake-vultr-key")
    monkeypatch.setattr("operia_crm.ai.runtime.request.urlopen", lambda req, timeout: R())
    from operia_crm.ai.runtime import _call_vultr

    try:
        _call_vultr(
            {
                "base_url": "https://api.vultrinference.com/v1",
                "model_name": "vultr-chat",
                "provider_ref": "VULTR_INFERENCE_API_KEY",
            },
            "hello",
        )
    except RuntimeError as exc:
        assert str(exc) == "Resposta vazia do Vultr"
    else:
        raise AssertionError("expected RuntimeError")


def test_vultr_failure_uses_local_fallback(monkeypatch):
    models = [
        {
            "provider_name": "Vultr",
            "model_name": "vultr-chat",
            "priority": 1,
            "base_url": "https://api.vultrinference.com/v1",
            "provider_ref": "VULTR_INFERENCE_API_KEY",
        }
    ]
    monkeypatch.setattr("operia_crm.ai.runtime.list_ai_models", lambda active=True: models)
    monkeypatch.setattr("operia_crm.ai.runtime._call_vultr", lambda model, prompt: (_ for _ in ()).throw(RuntimeError("Vultr sem chave configurada")))

    res = run_assisted_action("email", lead={"name": "A"})

    assert res["used_fallback"] is True
    assert res["provider_name"] == "fallback_local"
    assert res["content"]
    assert "Vultr sem chave configurada" in (res["error"] or "")
