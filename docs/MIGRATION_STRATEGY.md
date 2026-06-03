# MIGRATION STRATEGY — LeadOps Empório -> OperIA CRM

## Objetivo

Evoluir de uma base conceitual originalmente setorial (alimentação corporativa) para um produto CRM **multi-nicho**, comercialmente escalável e tecnicamente parametrizável, sem iniciar implementação nesta etapa.

## 1) Estratégia de evolução

- Tratar o LeadOps Empório como **fonte de aprendizado operacional**, não como produto final.
- Separar explicitamente:
  - **Core OperIA CRM (global e reaproveitável)**;
  - **Templates de Nicho (regras e linguagem específicas)**.
- Definir primeiro o “contrato conceitual” entre core e templates antes de qualquer decisão técnica.

## 2) Separação Core x Template

### Core multi-nicho (global)

- entidades comerciais universais (lead, conta, contato, oportunidade);
- funil parametrizável;
- deduplicação configurável;
- motor de score/prioridade com pesos;
- fila de execução diária;
- histórico de interações e auditoria;
- relatórios e exportação.

### Template específico (nicho)

- taxonomia comercial do setor;
- campos complementares;
- critérios de qualificação setoriais;
- etapas de funil especializadas;
- playbooks, scripts e mensagens de referência;
- pesos de score por contexto de mercado.

## 3) Fases de migração conceitual

### Fase 0.1 — Análise e generalização do LeadOps Empório (pré-técnica)

- inventariar conceitos existentes;
- classificar por: reaproveitar / parametrizar / descartar;
- formalizar limites do core;
- formalizar escopo do Template Alimentação Corporativa.

### Fase 0.2 — Modelagem de produto multi-nicho

- definir mapa de módulos globais;
- definir contrato entre módulos e templates;
- documentar critérios de aderência por nicho.

### Fase 0.3 — Validação comercial e narrativa

- testar posicionamento “OperIA CRM multi-nicho” com clientes-alvo;
- usar Empório como caso conceitual de origem e prova de método;
- ajustar proposta de valor por segmento prioritário.

### Fase 0.4 — Preparação para implementação

- consolidar backlog funcional e não funcional;
- priorizar MVP conceitual do core (sem codificar nesta fase);
- definir critérios de entrada para execução técnica.

## 4) O que reaproveitar, descartar e parametrizar

### Reaproveitar

- lógica de organização comercial diária;
- priorização por score;
- disciplina de registro e auditoria;
- operação assistida por IA com revisão humana obrigatória.

### Descartar (do núcleo)

- naming e linguagem exclusivos de alimentação corporativa;
- etapas e campos rígidos que não generalizam;
- premissas operacionais específicas de cozinha/logística alimentar.

### Parametrizar

- campos de qualificação;
- critérios de score;
- etapas do pipeline;
- mensagens e scripts;
- indicadores por nicho.

## 5) Critérios para iniciar implementação técnica

Só iniciar implementação quando os critérios abaixo forem atendidos:

1. Core multi-nicho documentado e validado internamente.
2. Template Alimentação Corporativa formalizado como template (não como núcleo).
3. Regras de separação global x nicho definidas em documentação.
4. Backlog de produto priorizado com escopo inicial claro.
5. Riscos críticos técnicos/comerciais mapeados com mitigação mínima.
6. Diretriz de IA assistiva (sem disparo automático cego) registrada como requisito.

## 6) Riscos técnicos e comerciais

### Técnicos

- acoplamento prematuro entre regras de nicho e domínio global;
- sobrecarga de parametrização sem governança;
- inconsistência de dados se deduplicação não for configurável por contexto.

### Comerciais

- mensagem confusa (“produto novo” com percepção de nicho antigo);
- dificuldade de precificação se templates parecerem customização sob medida;
- promessa de automação indevida em canais sensíveis (WhatsApp/e-mail).

## 7) Resultado esperado desta etapa documental

Ao final desta etapa, o OperIA CRM deve ter:

- visão estratégica clara de generalização;
- fronteiras nítidas entre core e templates;
- plano de transição conceitual do LeadOps Empório para Template Alimentação Corporativa;
- critérios objetivos para decidir o momento de começar implementação.
