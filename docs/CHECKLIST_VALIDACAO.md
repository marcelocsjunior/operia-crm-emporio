# Checklist de Validacao - OperIA CRM v3

## Antes de iniciar

- Escopo fechado.
- Branch correta.
- Main atualizada.
- Sem dados reais no diff.

## Validacao tecnica

- py_compile
- compileall
- pytest
- import operia_crm
- git diff --check

## Validacao manual

1. Painel Comercial Premium.
2. Leads.
3. Importacao.
4. Propostas.
5. Agenda e Historico.
6. Export e Backup.
7. Central IA.
8. WhatsApp revisado abrindo WhatsApp Business quando aplicavel.
9. WhatsApp Web preservado como fallback/browser.
10. Gmail abrindo fluxo de compose/login, sem cair em pagina comercial do Workspace.
11. App e-mail via mailto.
12. Registro WhatsApp + D+2 com checkbox.
13. Registro e-mail + D+3 com checkbox.
14. Confirmar que nada e enviado automaticamente.

## Bloqueios de merge

- Segredo no diff.
- Banco real versionado.
- Backup versionado.
- Arquivo real de importacao versionado.
- Disparo externo automatico.
- Alteracao destrutiva sem confirmacao.
- Regressao em fluxo validado.
- WhatsApp revisado voltar a abrir handler generico quando a intencao for Business.
- Gmail voltar a abrir `workspace.google.com` como destino principal.

## Baseline atual

```text
OperIA CRM — GUI Comercial Premium validada
Base: main
Status: operacional
```

Documento de referencia:

```text
docs/GUI_COMERCIAL_PREMIUM_BASELINE.md
```

## Regra final

Validacao real vale mais que declaracao.
