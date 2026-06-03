# OperIA CRM — GUI Comercial Premium validada

## Estado oficial

```text
Base: main
Status: operacional
Data operacional: 2026-06-02
```

Esta baseline registra a versao operacional validada da GUI Comercial Premium do OperIA CRM apos o ciclo de portabilidade controlada da experiencia visual do `CRM_LEADSOPS` para o repositorio oficial `operia-crm`.

## Escopo validado

A entrega validada cobre a home comercial premium do OperIA CRM mantendo o backend oficial como fonte unica de dados, regras e registro interno.

Componentes validados:

- Painel Comercial premium.
- Top 5 automatico.
- Tamanho do lote IA.
- Lead do lote.
- Temperatura comercial.
- Funil com gargalos.
- Modo IA com revisao obrigatoria.
- Mensagem WhatsApp revisavel.
- E-mail revisavel.
- Acoes rapidas por canal.
- CRM detalhado preservado em segundo plano.
- Importacao, Central IA, Propostas, Agenda/Historico e Export/Backup preservados.

## Fluxo operacional aprovado

```text
IA prioriza e prepara.
Operador revisa.
Operador escolhe canal.
Operador confirma registro interno.
Nada externo e disparado automaticamente.
```

## Canais e travas validadas

### WhatsApp

- `WhatsApp revisado` prioriza WhatsApp Business no Android por intent direcionado ao pacote `com.whatsapp.w4b`.
- `WhatsApp Web` permanece como fallback/browser explicito.
- A mensagem usada e sempre a mensagem revisada pelo operador.
- O app apenas abre compose/conversa; nao envia automaticamente.

### Gmail e e-mail

- `Gmail` abre fluxo de composicao via `accounts.google.com/AccountChooser` com `continue` para Gmail Web compose.
- `App e-mail` permanece via `mailto:`.
- O app apenas abre a composicao; nao envia automaticamente.

### Registros internos

- `Registrar WhatsApp + D+2` exige checkbox de revisao humana.
- `Registrar e-mail + D+3` exige checkbox de revisao humana.
- `Pular por agora` nao executa acao destrutiva.
- Acoes sao registradas internamente no CRM, sem disparo externo automatico.

## Pull requests incorporados na baseline

- PR #36 — `feat: port LeadOps premium commercial GUI to OperIA CRM`
- PR #37 — `fix: make revised WhatsApp action prefer Business app`
- PR #38 — `fix: open Gmail compose instead of Workspace marketing page`

## Garantias preservadas

- Backend validado preservado.
- Banco e schema preservados.
- Importacao preservada.
- Deduplicacao e Central IA preservadas.
- Propostas preservadas.
- Agenda/Historico preservados.
- Export/Backup preservados.
- Sem tokens, secrets, bancos reais, backups reais ou dados sensiveis versionados.
- Sem WhatsApp API, Gmail API, SMTP, Selenium ou disparos externos automaticos.

## Validacao tecnica da fase

Validações executadas durante o ciclo:

```bash
./.venv/bin/python -m py_compile app.py pages/Config_IA.py
./.venv/bin/python -m compileall app.py pages src tests
./.venv/bin/python -m pytest -q
./.venv/bin/python -c "import operia_crm; print('OK')"
PYTHONPATH=src ./.venv/bin/python -c "import operia_crm; print('OK')"
git diff --check
```

Resultado operacional observado:

```text
pytest: 116 passed
main atualizada
porta oficial: 8501
status: validado e operando
```

## Validacao manual registrada

Validado por Marcelo em ambiente real:

- OperIA CRM acessivel na porta oficial `8501`.
- GUI Comercial Premium validada visualmente.
- WhatsApp Business validado no Android.
- WhatsApp Web preservado.
- Gmail corrigido para fluxo compose/login.
- App e-mail preservado.
- Registros D+2/D+3 permanecem manuais e protegidos por checkbox.

## Regra de governanca a partir desta baseline

Esta baseline passa a ser referencia operacional da GUI Comercial Premium.

Antes de qualquer nova mudanca:

1. Preservar backend, banco, schema e fluxos validados.
2. Nao reintroduzir envio externo automatico.
3. Nao versionar dados reais, bancos, tokens, secrets, backups ou arquivos de importacao reais.
4. Validar visualmente no ambiente real quando a mudanca envolver UI mobile/canais.
5. Preferir hotfix cirurgico para regressao operacional.

## Veredito

```text
OperIA CRM — GUI Comercial Premium validada
Base: main
Status: operacional
```
