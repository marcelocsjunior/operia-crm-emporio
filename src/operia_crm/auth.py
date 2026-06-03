from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
import secrets


HASH_ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 390_000
SESSION_AUTH_KEY = "operia_auth_authenticated"
SESSION_USER_KEY = "operia_auth_user"
LOGIN_ERROR_KEY = "operia_auth_login_error"


@dataclass(frozen=True)
class AuthConfig:
    enabled: bool
    user: str | None = None
    password_hash: str | None = None

    @property
    def is_complete(self) -> bool:
        return bool(self.user and self.password_hash)


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def read_auth_config(environ: dict[str, str] | None = None) -> AuthConfig:
    source = os.environ if environ is None else environ
    return AuthConfig(
        enabled=_is_truthy(source.get("OPERIA_AUTH_ENABLED")),
        user=(source.get("OPERIA_AUTH_USER") or "").strip() or None,
        password_hash=(source.get("OPERIA_AUTH_PASSWORD_HASH") or "").strip() or None,
    )


def generate_password_hash(
    password: str,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    salt: bytes | None = None,
) -> str:
    if not password:
        raise ValueError("password must not be empty")
    if iterations < 100_000:
        raise ValueError("iterations must be at least 100000")

    salt_bytes = salt if salt is not None else secrets.token_bytes(16)
    if not salt_bytes:
        raise ValueError("salt must not be empty")

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        iterations,
    )
    return f"{HASH_ALGORITHM}${iterations}${salt_bytes.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password or not password_hash:
        return False

    try:
        algorithm, iterations_raw, salt_hex, digest_hex = password_hash.split("$", 3)
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except (TypeError, ValueError):
        return False

    if algorithm != HASH_ALGORITHM or iterations <= 0 or not salt or not expected_digest:
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def authenticate_credentials(username: str, password: str, config: AuthConfig) -> bool:
    if not config.enabled or not config.is_complete:
        return False
    if not hmac.compare_digest(username.strip(), config.user or ""):
        return False
    return verify_password(password, config.password_hash)


def apply_streamlit_auth_guard() -> AuthConfig:
    import streamlit as st

    config = read_auth_config()
    if not config.enabled:
        return config

    if st.session_state.get(SESSION_AUTH_KEY) and st.session_state.get(SESSION_USER_KEY) == config.user:
        with st.sidebar:
            st.caption(f"Autenticado: {config.user}")
            if st.button("Sair", key="operia_auth_logout"):
                st.session_state.pop(SESSION_AUTH_KEY, None)
                st.session_state.pop(SESSION_USER_KEY, None)
                st.session_state.pop(LOGIN_ERROR_KEY, None)
                st.rerun()
        return config

    st.title("OperIA CRM — Empório")
    st.caption("Acesso restrito")

    if not config.is_complete:
        st.warning("Login habilitado, mas credenciais não configuradas.")
        st.stop()

    with st.form("operia_auth_login_form"):
        username = st.text_input("Usuário", key="operia_auth_username")
        password = st.text_input("Senha", type="password", key="operia_auth_password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        if authenticate_credentials(username, password, config):
            st.session_state[SESSION_AUTH_KEY] = True
            st.session_state[SESSION_USER_KEY] = config.user
            st.session_state.pop(LOGIN_ERROR_KEY, None)
            st.rerun()
        st.session_state[LOGIN_ERROR_KEY] = True

    if st.session_state.get(LOGIN_ERROR_KEY):
        st.caption("Credenciais inválidas.")

    st.stop()
