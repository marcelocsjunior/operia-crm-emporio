# Login MVP

O login interno do OperIA CRM é controlado por variáveis de ambiente. Quando `OPERIA_AUTH_ENABLED` não existe ou está como `false`, o app mantém o comportamento atual e abre sem autenticação.

## Habilitar

Gere o hash da senha no ambiente do projeto, sem digitar a senha na linha de comando:

```bash
python - <<'PY'
from getpass import getpass
from operia_crm.auth import generate_password_hash

print(generate_password_hash(getpass("Senha: ")))
PY
```

Configure o env do serviço com os valores abaixo, sem salvar senha em texto puro:

```env
OPERIA_AUTH_ENABLED=true
OPERIA_AUTH_USER=admin
OPERIA_AUTH_PASSWORD_HASH=pbkdf2_sha256$390000$<salt_hex>$<hash_hex>
```

Reinicie a aplicação após alterar o env.

## Desabilitar temporariamente

```env
OPERIA_AUTH_ENABLED=false
```

Também é possível remover `OPERIA_AUTH_ENABLED`; ausência da variável equivale a login desligado.

## Observação operacional

Em HTTP público, esse login é apenas uma proteção mínima para LAB. Produção deve usar HTTPS e uma camada externa adequada, como proxy autenticado, VPN ou Access.
