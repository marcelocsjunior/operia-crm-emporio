# Validacao sintetica — OperIA CRM Emporio

## Objetivo

Validar o Modo Operacional Emporio com massa totalmente ficticia.

## Arquivo de teste

`samples/emporio_synthetic_leads.csv`

## O que validar

- importacao do CSV sintetico;
- preenchimento dos campos Emporio;
- eventos proximos como prioridade;
- propostas e cardapios como retorno pendente;
- cliente corporativo e refeicao recorrente com peso maior;
- contato sem proxima acao como parado;
- perdido e fechado fora da prioridade ativa;
- mensagens assistidas especificas do Emporio;
- fluxo apenas assistido, sem envio automatico.

## Roteiro manual

1. Atualizar a branch local.
2. Subir o app Streamlit.
3. Abrir o app.
4. Entrar em Importacao.
5. Importar o arquivo CSV sintetico.
6. Conferir previa da importacao.
7. Confirmar importacao.
8. Abrir Painel Comercial.
9. Conferir os KPIs operacionais.
10. Abrir Fila operacional.
11. Conferir se eventos proximos, propostas/cardapios e oportunidades corporativas aparecem no topo.
12. Abrir Modo IA com revisao.
13. Conferir as mensagens sugeridas.

## Cenarios cobertos

| Cenario | Resultado esperado |
|---|---|
| Evento proximo | Prioridade alta |
| Reserva proxima | Item operacional relevante |
| Proposta/cardapio enviado | Retorno pendente |
| Cliente corporativo | Peso maior |
| Marmita/refeicao recorrente | Peso maior |
| Parceria | Oportunidade operacional |
| Reativacao | Mensagem de retomada |
| Sem proxima acao | Contato parado |
| Baixa urgencia | Nao domina fila |
| Perdido | Nao domina fila ativa |
| Confirmado / fechado | Fora da prioridade ativa |

## Criterios de aceite

- O CSV importa corretamente.
- A importacao antiga permanece compativel.
- Os campos Emporio aparecem preenchidos.
- A fila operacional prioriza corretamente.
- As mensagens sao especificas do Emporio.
- Nenhum dado real e usado.

## Proximos passos

- Validar com operador.
- Criar PR separado para proposta/cardapio comercial assistido.
- Criar PR separado para relatorio diario do Emporio.
