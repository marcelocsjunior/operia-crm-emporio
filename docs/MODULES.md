# MODULES — OperIA CRM

## Princípio de Arquitetura de Produto (conceitual)

O OperIA CRM deve separar explicitamente:

- **Core comum (global)**: módulos reutilizáveis para qualquer nicho;
- **Templates de nicho**: regras, linguagem e playbooks específicos.

Essa separação evita acoplamento setorial no núcleo e acelera expansão multi-nicho.

## Core comum do OperIA CRM (módulos globais)

### OperIA Leads

Módulo para entrada, organização e qualificação inicial de leads com estrutura padronizada entre segmentos.

### OperIA Pipeline

Módulo para gestão do funil comercial com etapas parametrizáveis, movimentação de oportunidades e visibilidade por fase.

### OperIA Follow-up

Módulo para controle de retornos, tarefas e cadências de contato (fila diária de ação e próximos passos).

### OperIA Insight

Módulo de inteligência para score, alertas e recomendações operacionais, apoiando decisão comercial.

### OperIA Messages

Módulo para histórico de interações (mensagens, e-mails, ligações e observações), sempre com registro da ação humana.

### OperIA Reports

Módulo de relatórios e indicadores para produtividade, conversão e previsibilidade comercial.

### OperIA Admin

Módulo administrativo para perfis de acesso, governança, parâmetros globais e rastreabilidade.

## Templates de Nicho (camada específica)

### OperIA Templates

Camada para criação e aplicação de templates por nicho, contendo:

- campos setoriais;
- regras de qualificação;
- estágios de funil especializados;
- pesos de score por contexto;
- playbooks e linguagem comercial.

## Template Alimentação Corporativa (herdeiro conceitual do LeadOps Empório)

O legado do LeadOps Empório deve ser tratado como **template futuro** chamado **Template Alimentação Corporativa**, e não como definição do produto inteiro.

Esse template herda:

- critérios comerciais de contratos corporativos de alimentação;
- fluxos de negociação típicos do setor;
- mensagens orientadas ao contexto de refeições corporativas.

## Diretriz operacional transversal

O core e os templates devem respeitar o mesmo fluxo:

1. sistema organiza e prioriza;
2. IA sugere abordagem;
3. operador humano revisa;
4. operador envia manualmente/no canal aberto;
5. operador registra no CRM.

**Sem promessa de disparo automático cego de WhatsApp/e-mail.**
