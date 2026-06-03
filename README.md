# OperIA CRM — Empório

Versão operacional do OperIA CRM adaptada para gestão comercial, relacionamento com clientes e rotinas internas do Empório Restaurante.

Esta baseline nasce a partir da base madura e validada do repositório `marcelocsjunior/operia-crm`, preservando a arquitetura operacional existente e aplicando apenas o rebrand mínimo necessário para o novo repositório técnico `operia-crm-emporio`.

## Status

Baseline técnica inicial do OperIA CRM — Empório.

Este projeto ainda não inclui verticalização profunda de restaurante, novos módulos específicos, alteração de schema, integração externa nova ou envio automático. O objetivo inicial é nascer limpo, funcional e seguro a partir da base operacional já validada.

## Stack

- Python
- Streamlit
- SQLite local
- Pacote interno `operia_crm`
- Testes com `pytest`

## Execução local

Crie ou ative uma virtualenv e instale as dependências:

```bash
python -m venv .venv
PATH=.venv/bin:$PATH python -m pip install -r requirements.txt -r requirements-dev.txt
```

Execute o app:

```bash
PATH=.venv/bin:$PATH python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

## Dados locais

O app usa SQLite local por padrão em `data/operia_crm.db`, ou no caminho definido por `OPERIA_DB_PATH`.

Arquivos locais de operação, como bancos, imports, exports, anexos, backups, uploads e logs, não devem ser versionados. A política do repositório é manter dados reais sempre fora do Git.

## Secrets

Não versionar `.env`, `*.env`, `.streamlit/secrets.toml`, tokens, chaves de API, senhas ou credenciais.

Referências a provedores externos devem ficar em variáveis locais ou secrets do ambiente. A IA continua assistiva: prepara, orienta e registra internamente somente após aprovação do operador. Nada é enviado automaticamente pelo bootstrap.

## Validação

Validações esperadas para a baseline:

```bash
python -m py_compile app.py pages/Config_IA.py
python -m compileall app.py pages src tests
python -m pytest -q
python -c "import operia_crm; print('OK')"
PYTHONPATH=src python -c "import operia_crm; print('OK')"
git diff --check
```

## Documentação

- `docs/BASELINE_EMPORIO.md`: registro do PR #1 e escopo da baseline.
- `docs/GUI_COMERCIAL_PREMIUM_BASELINE.md`: referência da base operacional madura herdada do OperIA CRM.

## Diretriz operacional

Preservar os fluxos validados antes de qualquer nova feature. Backend validado é patrimônio.
