# Runbook Local Managed - OperIA CRM v3

## Objetivo

Guia operacional para executar, validar e manter o OperIA CRM v3 em ambiente local gerenciado.

## Baseline

- Branch oficial: main
- Base validada: PR #33
- SHA esperado: afa8e01311aadeb7c3f2ab399094db0f46d6d17c

## Ambiente padrao

- Projeto: diretório local do repositório `operia-crm-emporio`
- Porta: 8501
- URL local: http://10.0.0.146:8501
- Python preferencial: ./.venv/bin/python

## Atualizar codigo local

```bash
cd /caminho/local/operia-crm-emporio
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Confirmar se o HEAD retornado bate com o baseline esperado.

## Subir aplicacao

```bash
cd /caminho/local/operia-crm-emporio
./.venv/bin/python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

## Validacao rapida

1. Abrir a URL local.
2. Conferir Painel Comercial.
3. Conferir Leads.
4. Conferir Importacao.
5. Conferir Central IA.
6. Conferir Propostas.
7. Conferir Agenda e Historico.
8. Conferir Export e Backup.

## Importacao por servidor

Pasta operacional:

```text
imports/inbox
```

Fluxo:

1. Copiar CSV ou XLSX para a pasta inbox.
2. Abrir aba Importacao.
3. Escolher arquivo salvo no servidor.
4. Carregar arquivo.
5. Revisar diagnostico.
6. Confirmar importacao.

## Regras de seguranca operacional

- Nao versionar dados reais.
- Nao versionar banco local.
- Nao versionar backups.
- Nao versionar arquivos importados reais.
- Nao versionar credenciais.
- Nao executar disparo externo automatico.
- Nao fazer merge de duplicidade sem revisao.
- Nao alterar status critico sem aprovacao.

## Rollback operacional

Se uma alteracao funcional falhar:

1. Parar a aplicacao.
2. Voltar para a main validada.
3. Confirmar HEAD esperado.
4. Subir novamente.
5. Validar fluxo minimo.

## Evidencias recomendadas

Registrar antes de merge funcional:

- SHA da branch.
- Resultado dos testes.
- Prints das telas alteradas.
- Resultado de importacao, se aplicavel.
- Confirmacao de que nada externo foi enviado.

## Diretriz final

Este runbook nao substitui validacao real. Em producao local, declaracao sem evidencia e igual backup nunca testado: bonito ate o dia em que precisa.
