# Prompt para Codex — Implementação do OperIA CRM v1

Trabalhe no repositório `marcelocsjunior/operia-crm`.

## Objetivo

Implementar a primeira versão funcional do OperIA CRM conforme a especificação `docs/OPERIA_CRM_V1_SPEC.md`.

## Regras obrigatórias

- Não usar dados reais.
- Não versionar `.env`, bancos SQLite, backups, anexos ou arquivos sensíveis.
- Não implementar envio automático de WhatsApp ou e-mail.
- Não implementar WhatsApp API, SMTP, Gmail API ou Outlook API no MVP.
- Toda comunicação externa deve ser assistida: abrir canal com texto pré-preenchido e exigir confirmação manual do operador.
- Manter SQLite como banco local inicial.
- Preparar camada de dados para migração futura para PostgreSQL.
- Usar fallback local para IA e Gemini apenas quando configurado.
- Nunca gravar chave Gemini no código.

## Entregáveis esperados

Criar uma aplicação inicial funcional com:

- Cockpit Comercial;
- cadastro de leads;
- importação CSV/XLSX com prévia, mapeamento, validação e deduplicação;
- funil comercial simples;
- agenda de follow-ups;
- histórico estruturado;
- WhatsApp assistido;
- e-mail assistido;
- propostas/orçamentos com numeração `PROP-0001`;
- geração de PDF simples de proposta;
- anexos seguros por lead/cliente;
- conversão de lead ganho em cliente;
- exportação CSV/Excel;
- PDF executivo simples;
- score híbrido 0–100;
- IA assistiva local + Gemini opcional;
- backup local básico de banco + anexos;
- auditoria mínima de eventos.

## Arquitetura sugerida

Use estrutura limpa, evitando lógica misturada na UI:

```text
app.py
src/operia_crm/
  config/
  database/
  models/
  repositories/
  services/
  ai/
  reports/
  attachments/
  imports/
  backup/
  ui/
  utils/
tests/
docs/
data/.gitkeep
attachments/.gitkeep
```

## Requisitos técnicos

- Python 3.11+.
- Streamlit ou stack web simples, conforme padrão do repositório, se já definido.
- SQLite.
- ReportLab ou biblioteca equivalente para PDF.
- Pandas/OpenPyXL para importação/exportação.
- Testes mínimos para deduplicação, score, numeração de proposta e validação de anexos.

## Branch e PR

Criar branch:

```text
feat/operia-crm-v1-mvp
```

Abrir PR com título:

```text
feat: implementar MVP funcional do OperIA CRM v1
```

Descrição do PR deve conter:

- resumo do que foi implementado;
- como executar localmente;
- variáveis de ambiente;
- comandos de teste;
- checklist de segurança;
- limitações conhecidas;
- próximos passos.

## Critérios de aceite

A implementação deve atender os critérios listados na seção `Critérios de aceite do MVP` da especificação.

Se algum item não for implementado por limitação técnica, documentar explicitamente no PR e criar item em backlog.
