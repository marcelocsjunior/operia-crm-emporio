import pytest

from operia_crm.auth import (
    AuthConfig,
    authenticate_credentials,
    generate_password_hash,
    read_auth_config,
    verify_password,
)


def test_generate_and_verify_password_hash():
    password_hash = generate_password_hash(
        "senha-forte",
        iterations=100_000,
        salt=bytes.fromhex("00112233445566778899aabbccddeeff"),
    )

    assert password_hash.startswith("pbkdf2_sha256$100000$")
    assert verify_password("senha-forte", password_hash)
    assert not verify_password("senha-errada", password_hash)


def test_generated_hash_uses_random_salt_by_default():
    first = generate_password_hash("senha-forte")
    second = generate_password_hash("senha-forte")

    assert first != second
    assert verify_password("senha-forte", first)
    assert verify_password("senha-forte", second)


@pytest.mark.parametrize(
    "password_hash",
    [
        "",
        None,
        "plain-text",
        "pbkdf2_sha256$bad$00$11",
        "sha256$100000$00$11",
        "pbkdf2_sha256$100000$$11",
        "pbkdf2_sha256$100000$00$",
    ],
)
def test_verify_password_rejects_invalid_hashes(password_hash):
    assert not verify_password("senha-forte", password_hash)


def test_read_auth_config_defaults_to_disabled():
    config = read_auth_config({})

    assert config == AuthConfig(enabled=False, user=None, password_hash=None)


def test_read_auth_config_parses_enabled_and_trims_values():
    config = read_auth_config(
        {
            "OPERIA_AUTH_ENABLED": "true",
            "OPERIA_AUTH_USER": " admin ",
            "OPERIA_AUTH_PASSWORD_HASH": " pbkdf2_sha256$100000$00$11 ",
        }
    )

    assert config.enabled is True
    assert config.user == "admin"
    assert config.password_hash == "pbkdf2_sha256$100000$00$11"


def test_authenticate_credentials_requires_enabled_complete_config():
    password_hash = generate_password_hash("senha-forte", iterations=100_000, salt=b"salt-1234567890")

    assert authenticate_credentials(
        "admin",
        "senha-forte",
        AuthConfig(enabled=True, user="admin", password_hash=password_hash),
    )
    assert not authenticate_credentials(
        "admin",
        "senha-forte",
        AuthConfig(enabled=False, user="admin", password_hash=password_hash),
    )
    assert not authenticate_credentials(
        "admin",
        "senha-forte",
        AuthConfig(enabled=True, user=None, password_hash=password_hash),
    )


def test_authenticate_credentials_rejects_wrong_user_or_password():
    password_hash = generate_password_hash("senha-forte", iterations=100_000, salt=b"salt-1234567890")
    config = AuthConfig(enabled=True, user="admin", password_hash=password_hash)

    assert not authenticate_credentials("outro", "senha-forte", config)
    assert not authenticate_credentials("admin", "senha-errada", config)
