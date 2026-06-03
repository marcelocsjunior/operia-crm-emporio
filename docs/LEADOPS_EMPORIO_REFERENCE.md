# LEADOPS EMPÓRIO REFERENCE — Base Conceitual para o OperIA CRM

## 1) O que era o LeadOps CRM Empório

O LeadOps CRM Empório v1 foi concebido como um CRM de prospecção B2B para alimentação corporativa, com foco em transformar listas dispersas em rotina comercial executável. Na prática, o sistema ajudava a organizar empresas com potencial para contratar marmitas, refeições, lanches e café da manhã corporativo (ex.: obras, mineradoras, construtoras, terceirizadas, transportadoras e prestadoras de serviço).

A proposta central era reduzir improviso comercial: priorizar quem abordar, quando abordar e com qual argumento, mantendo registro do que foi feito para evitar perda de contexto.

## 2) Conceitos que devem ser reaproveitados no OperIA CRM

Os aprendizados mais valiosos e reaproveitáveis como núcleo multi-nicho são:

- **Cadastro/importação de leads** com estrutura mínima padronizada.
- **Deduplicação por chave operacional** para evitar retrabalho e duplicidade de carteira.
- **Score e prioridade comercial** para ordenar esforço de time.
- **Funil de vendas** com etapas explícitas e critérios de avanço.
- **Fila diária de ação** orientada a tarefas e próximos passos.
- **Geração assistida por IA** de mensagens, e-mails e scripts (apoio à execução humana).
- **Registro de interações** com trilha histórica por lead/oportunidade.
- **Auditoria de alterações** para governança e rastreabilidade.
- **Exportação CSV** para portabilidade de dados.
- **Operação local ou em rede controlada** quando exigido pelo cliente.

## 3) Partes específicas demais do nicho de alimentação corporativa

Os elementos abaixo devem sair do núcleo e virar template setorial:

- Terminologias de oferta (marmitas, cardápio, degustação, café da manhã corporativo).
- Critérios de qualificação ligados a volume de refeições, janelas de entrega e tipo de contrato alimentar.
- Etapas de funil muito específicas (ex.: degustação técnica, ajuste de cardápio, validação nutricional).
- Campos e score excessivamente ancorados em operação de cozinha/logística alimentar.
- Scripts comerciais centrados apenas em dor de alimentação corporativa.

## 4) Riscos de apenas renomear LeadOps para OperIA

Renomear sem generalizar o produto cria risco estratégico e operacional:

- **Risco de posicionamento**: mercado percebe produto “fantasiado”, mas ainda de nicho único.
- **Risco de adoção**: clientes de outros segmentos não se reconhecem no fluxo.
- **Risco de arquitetura**: regras hardcoded de um nicho contaminam módulos globais.
- **Risco comercial**: time de vendas fica limitado por linguagem setorial.
- **Risco de manutenção**: cada novo nicho vira exceção manual em vez de configuração.
- **Risco de promessa indevida**: confundir IA assistiva com automação cega de disparos.

## 5) Como transformar Empório em Template Alimentação Corporativa

Estratégia recomendada:

1. **Extrair o core comum** (lead, pipeline, follow-up, histórico, auditoria, priorização).
2. **Mapear tudo que for regra de alimentação** para um pacote de configuração.
3. **Criar o Template Alimentação Corporativa** contendo:
   - vocabulário do nicho;
   - campos específicos;
   - etapas de funil especializadas;
   - pesos de score por contexto;
   - playbooks e mensagens base.
4. **Isolar prompts/sugestões de IA por template**, sem misturar semânticas de nichos.
5. **Validar template separadamente do core** para manter evolução desacoplada.

## 6) Funcionalidades que devem virar núcleo comum do OperIA CRM

Para suportar visão multi-nicho, o core deve incluir:

- Gestão de leads e contas.
- Motor de deduplicação configurável por chave operacional.
- Pipeline parametrizável por etapas.
- Fila de ações diária com agenda de follow-up.
- Motor de score e prioridade com pesos configuráveis.
- Registro de interações omnicanal (sem disparo automático cego).
- IA assistiva para sugestão de abordagem (sempre com revisão humana).
- Auditoria e trilha de alterações.
- Relatórios operacionais e exportação CSV.
- Camada de templates (nicho) separada do domínio global.

## 7) Princípio operacional obrigatório (mantido)

O OperIA CRM deve preservar, de forma explícita, o fluxo correto de atuação comercial:

1. Sistema organiza e prioriza leads;
2. IA sugere abordagem e mensagem;
3. Operador humano revisa;
4. Operador envia manualmente (ou pelo canal aberto);
5. Operador registra a ação no CRM.

**Diretriz crítica:** o produto não deve prometer disparo automático real de WhatsApp ou e-mail de forma cega/autônoma.
