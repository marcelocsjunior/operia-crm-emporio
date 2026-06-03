# Modo Operacional Empório

## Objetivo

Transformar a baseline do OperIA CRM — Empório em uma ferramenta operacional para controlar oportunidades reais de restaurante, eventos, encomendas, reservas, parcerias e atendimento corporativo.

O modo operacional responde ao dia a dia do operador:

- quem precisa de retorno hoje;
- quem aguarda proposta/cardápio;
- quem está aguardando retorno;
- quais eventos ou entregas estão próximos;
- quais oportunidades têm maior potencial;
- quais contatos estão parados;
- qual próxima ação deve ser executada com revisão humana.

## Campos novos

Os campos abaixo foram adicionados à entidade `leads` de forma aditiva:

- `opportunity_type`: tipo de oportunidade.
- `event_or_delivery_date`: data do evento, entrega ou reserva.
- `estimated_value`: valor estimado.
- `people_count`: quantidade de pessoas.
- `source_channel`: canal de origem.
- `emporio_status`: status operacional Empório.
- `next_action`: próxima ação operacional.
- `operational_notes`: observação operacional.

## Tipos de oportunidade

- Reserva
- Evento
- Encomenda
- Marmita / refeição recorrente
- Cliente corporativo
- Parceria
- Reativação
- Outro

## Funil Empório

- Novo contato
- Qualificar demanda
- Proposta/cardápio enviado
- Aguardando retorno
- Confirmado / fechado
- Perdido
- Reativar futuramente

## Regras de priorização

A prioridade operacional considera:

- evento, entrega ou reserva nos próximos 7 dias;
- proposta/cardápio enviado ou aguardando retorno;
- valor estimado;
- quantidade de pessoas;
- oportunidade corporativa ou recorrente;
- ausência de próxima ação;
- contato sem canal público válido;
- status operacional atual.

Classificação:

- Alta
- Média
- Baixa

Temperatura:

- Quente
- Morno
- Frio

Critérios implementados:

- Evento/entrega nos próximos 7 dias recebe prioridade alta.
- Proposta/cardápio enviado ou aguardando retorno recebe peso alto.
- Cliente corporativo e marmita/refeição recorrente recebem peso maior.
- Valor estimado maior que zero aumenta prioridade.
- Quantidade de pessoas relevante aumenta prioridade.
- Falta de telefone, WhatsApp ou e-mail continua sendo alerta de cadastro incompleto.

## Importação

As colunas antigas continuam funcionando.

Colunas opcionais em português:

- `tipo_oportunidade`
- `data_evento_ou_entrega`
- `valor_estimado`
- `quantidade_pessoas`
- `canal_origem`
- `status_emporio`
- `proxima_acao`
- `observacao_operacional`

Aliases em inglês:

- `opportunity_type`
- `event_or_delivery_date`
- `estimated_value`
- `people_count`
- `source_channel`
- `emporio_status`
- `next_action`
- `operational_notes`

Regras preservadas:

- Nome continua obrigatório.
- Pelo menos um contato público válido continua obrigatório: telefone, WhatsApp ou e-mail.
- Deduplicação antiga continua ativa.
- Duplicado forte não é importado.
- CSV/XLSX real de operação não deve ser versionado.

## Mensagens assistidas

O modo Empório prepara mensagens para:

- primeiro contato;
- retorno de proposta/cardápio;
- confirmação de reserva, evento ou encomenda;
- reativação de cliente;
- cliente corporativo;
- parceria;
- marmita/refeição recorrente.

## Garantias de não envio automático

O sistema não envia mensagens automaticamente.

Não foi adicionada integração com:

- WhatsApp API;
- Gmail API;
- SMTP;
- Selenium;
- campanhas em massa;
- qualquer serviço externo de envio.

O app apenas prepara texto, abre canais de composição quando o operador escolhe e registra ações internas depois de revisão humana.

## Validações executadas

Registrar no PR os resultados de:

```bash
./.venv/bin/python -m py_compile app.py pages/Config_IA.py
./.venv/bin/python -m compileall app.py pages src tests
./.venv/bin/python -m pytest -q
./.venv/bin/python -c "import operia_crm; print('OK')"
PYTHONPATH=src ./.venv/bin/python -c "import operia_crm; print('OK')"
git diff --check
curl -I http://127.0.0.1:8501
```

## Próximos passos

- Validar fluxo com dados sintéticos.
- Criar PR separado para proposta/cardápio comercial.
- Criar PR separado para relatório diário do Empório.
- Avaliar ajustes finos de linguagem após uso operacional real.
