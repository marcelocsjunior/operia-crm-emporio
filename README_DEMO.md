# README_DEMO — OperIA CRM v1 (MVP)

## 1) Preparação do ambiente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```

## 2) Comandos de validação

```bash
python -m py_compile app.py
python -m compileall app.py src tests
python -m pytest -q
python -c "import operia_crm; print('OK')"
```

## 3) Execução local

```bash
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

## 4) Fluxo objetivo de demo (5 a 10 min)

1. **Cockpit**
   - Mostrar aviso de ambiente Local Managed / SQLite local.
   - Mostrar status operacional do banco (caminho, existência, tamanho).
2. **Cadastrar lead**
   - Criar 1 lead com nome + telefone/e-mail.
3. **Importar CSV/XLSX**
   - Importar arquivo de exemplo com colunas `name`/`nome`.
   - Mostrar prévia, dedupe e confirmar importação.
   - Validar resumo: total, importados, ignorados por duplicidade, sem nome, sem contato e erros.
4. **Confirmar interação assistida**
   - Registrar interação de WhatsApp ou e-mail assistido.
   - Confirmar manualmente em Agenda/Histórico.
5. **Criar proposta**
   - Gerar proposta para um lead.
   - Confirmar numeração sequencial (`PROP-0001`, `PROP-0002`, ...).
   - Gerar PDF e validar layout básico.
6. **Backup local**
   - Gerar backup `.db`.
   - Mostrar caminho (absoluto e relativo) e testar download do arquivo.

## 5) Limitações atuais do MVP

- Operação **Local Managed** com SQLite local (sem multiusuário distribuído).
- WhatsApp e e-mail são assistidos por link e confirmação manual (sem envio automático).
- Sem integrações oficiais de API externa para canais.
- Sem automações de fluxo complexas.
- Foco em validação operacional do funil comercial em ambiente local.
