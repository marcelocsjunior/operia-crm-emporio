# Baseline OperIA CRM — Empório

## Status da baseline

Baseline técnica inicial do repositório `marcelocsjunior/operia-crm-emporio`.

Esta entrega cria o ponto de partida operacional do OperIA CRM — Empório a partir da base madura do `marcelocsjunior/operia-crm`, preservando a arquitetura validada e aplicando apenas ajustes mínimos de branding, documentação e proteção de dados locais.

## Origem do projeto

- Origem técnica: `marcelocsjunior/operia-crm`
- Destino técnico: `marcelocsjunior/operia-crm-emporio`
- Nome visual/documental principal: `OperIA CRM — Empório`
- Finalidade: gestão comercial, relacionamento com clientes e rotinas internas do Empório Restaurante.

## Escopo do PR #1

- Bootstrap inicial da base funcional.
- Preservação da estrutura Streamlit, SQLite local, Python, `app.py`, `pages/`, `src/`, `tests/`, `docs/`, `README.md`, `.gitignore` e arquivos de dependência.
- Rebrand mínimo para `OperIA CRM — Empório`.
- README inicial do novo projeto.
- `.gitignore` reforçado contra dados reais, bancos, anexos, imports, exports, backups, logs e secrets.
- Remoção de caminho absoluto local herdado no diretório padrão de importação.

## Fora do escopo neste PR

- Feature nova.
- Módulos específicos de restaurante.
- Alteração de schema.
- Integração externa nova.
- Envio automático.
- Alteração de fluxos de WhatsApp, Gmail/e-mail, propostas, importação, histórico, backup/export ou Central IA.
- Refatoração de backend.
- Redesign.

## Validações executadas

Registrar no PR os resultados de:

```bash
python -m py_compile app.py pages/Config_IA.py
python -m compileall app.py pages src tests
python -m pytest -q
python -c "import operia_crm; print('OK')"
PYTHONPATH=src python -c "import operia_crm; print('OK')"
git diff --check
```

## Limitações conhecidas

- A verticalização específica para restaurante ainda não foi implementada.
- O banco SQLite local é criado em runtime e não faz parte do repositório.
- Imports, exports, anexos, backups e logs são artefatos operacionais locais e permanecem fora do Git.
- Qualquer integração externa depende de configuração local explícita e revisão operacional.

## Próximos passos sugeridos

- Validar visualmente a UI Streamlit em ambiente local.
- Planejar PRs pequenos para ajustes Empório específicos, sem misturar bootstrap com feature.
- Definir dados demonstrativos sintéticos apenas se forem necessários para documentação ou testes futuros.
- Manter revisão operacional antes de qualquer merge.
