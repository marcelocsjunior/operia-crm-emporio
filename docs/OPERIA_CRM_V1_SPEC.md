# OPERIA CRM — Especificação Funcional v1

Status: especificação funcional consolidada para orientar implementação futura.
Produto: OperIA CRM.
Fornecedor: Biotech TI.
Escopo: MVP comercial inicial com execução Local Managed e evolução breve para Hosted Managed.

---

## 1. Visão do produto

O OperIA CRM é um CRM operacional com IA assistiva para pequenos negócios organizarem leads, clientes, propostas, follow-ups, interações e rotina comercial.

O produto deve ser vendido externamente apenas como **OperIA CRM**. Termos como Start, Local Managed, Hosted Managed, template ativo e modo de IA devem ser tratados como visão interna de produto, implantação e operação.

### Proposta central

Ajudar pequenos negócios a não perderem oportunidades por falta de organização, follow-up, histórico e rotina comercial.

### Posicionamento comercial

CRM simples, acessível e assistido por IA para pequenos negócios venderem com mais organização, previsibilidade e ação diária.

---

## 2. Público-alvo

O MVP deve atender pequenos negócios de qualquer nicho, com foco em operação comercial simples.

Perfis prioritários:

- prestadores de serviço;
- pequenas empresas B2B;
- assistência técnica;
- consultorias locais;
- empresas de TI e suporte técnico;
- comércio local com venda consultiva;
- negócios que hoje operam com WhatsApp, planilha e memória do dono.

---

## 3. Modelo de implantação

### Fase inicial: Local Managed

A primeira versão será instalada conforme a estrutura do cliente, avaliada pela Biotech TI.

Cenários possíveis:

- notebook ou PC local;
- PC dedicado;
- mini servidor;
- VM local;
- estrutura alternativa definida pela Biotech TI.

A decisão técnica deve ser tomada caso a caso, considerando maturidade do cliente, risco, backup, rede, acesso e suporte.

### Evolução breve: Hosted Managed

A próxima etapa será hospedagem gerenciada pela Biotech TI, com acesso via navegador, backup centralizado e operação mais controlada.

Não tratar Hosted Managed como SaaS completo no início. SaaS multiempresa, billing, RBAC avançado e tenant isolation entram em fase posterior.

---

## 4. Modelo comercial

Modelo recomendado:

- implantação paga;
- mensalidade de suporte/gestão;
- customização pesada cobrada à parte;
- Hosted Managed com mensalidade superior em fase posterior.

Evitar venda única sem recorrência e evitar SaaS completo antes da maturidade técnica.

---

## 5. Arquitetura de produto

### Nome público

OperIA CRM.

### Visão interna

- plano interno: Start;
- modo de implantação: Local Managed / Hosted Managed;
- template ativo: Pequenos Negócios / TI & Suporte;
- IA: Local / Gemini / Híbrida;
- banco: SQLite no MVP, PostgreSQL no futuro.

### Camadas do produto

- core comum multi-nicho;
- templates por nicho;
- configurações aplicadas pela Biotech TI na implantação;
- visão cliente simplificada;
- visão técnica/admin para Biotech TI.

---

## 6. Templates iniciais

O MVP deve nascer com dois templates:

1. Pequenos Negócios / Serviços Gerais.
2. TI & Suporte Técnico.

Outros templates entram depois:

- Alimentação Corporativa;
- Clínicas e Consultórios;
- Automação Residencial / Serviços Técnicos.

Os templates devem ser prontos, mas ajustáveis pela Biotech TI na implantação. O cliente não deve editar livremente templates na primeira versão.

---

## 7. Tela inicial: Cockpit Comercial

A tela inicial deve ser o **Cockpit Comercial**.

Deve combinar:

- indicadores rápidos;
- fila de ações do dia;
- follow-ups atrasados;
- oportunidades quentes;
- propostas em aberto;
- alertas internos;
- resumo assistivo da IA.

### Cards principais

- leads totais;
- oportunidades quentes;
- follow-ups pendentes;
- follow-ups atrasados;
- propostas abertas/enviadas;
- valor potencial em propostas;
- negócios ganhos/perdidos.

### Fila inteligente

A priorização da fila deve combinar:

- atraso do follow-up;
- score comercial;
- status do funil;
- existência de proposta aberta/enviada;
- risco de oportunidade parada.

---

## 8. Leads

### Cadastro simples

Campos obrigatórios mínimos:

- nome do lead ou empresa;
- telefone/WhatsApp ou e-mail;
- status inicial;
- origem;
- próximo follow-up, quando aplicável.

Campos opcionais:

- cidade;
- segmento/nicho;
- observações;
- potencial comercial;
- serviço/produto de interesse.

Não haverá campo de responsável pelo lead no MVP, pois não haverá login forte.

### Origem do lead

Campo controlado com lista padrão:

- Indicação;
- WhatsApp;
- Instagram;
- Site;
- Google;
- Prospecção ativa;
- Evento;
- Cliente antigo;
- Parceria;
- Outro.

Para "Outro", permitir detalhe opcional.

---

## 9. Importação de leads

O MVP deve permitir importação por CSV e, se tecnicamente viável, XLSX.

Deve suportar:

- modelo padrão OperIA;
- mapeamento flexível de colunas;
- prévia antes da importação;
- validação de campos mínimos;
- detecção de duplicados;
- resumo pós-importação.

### Modelo padrão sugerido

- nome;
- empresa;
- telefone;
- whatsapp;
- email;
- cidade;
- segmento;
- origem;
- status;
- observacoes;
- proximo_followup.

### Deduplicação

A deduplicação deve ser inteligente, combinando:

- telefone/WhatsApp normalizado;
- e-mail normalizado;
- nome/empresa normalizados;
- cidade/segmento como apoio.

Classificações:

- duplicado forte: mesmo telefone ou mesmo e-mail;
- duplicado provável: nome/empresa parecido com cidade/segmento semelhante;
- não duplicado: dados suficientemente distintos.

Nenhuma mescla ou exclusão destrutiva deve ocorrer sem confirmação humana.

---

## 10. Funil comercial

Funil padrão inicial:

- Novo lead;
- Qualificar;
- Contato iniciado;
- Proposta enviada;
- Negociação;
- Ganho;
- Perdido;
- Follow-up futuro.

O funil deve ser padrão, mas editável pela Biotech TI na implantação.

Visão kanban simples deve existir, sem exigir drag-and-drop complexo no MVP.

---

## 11. Score comercial

Score híbrido:

- sistema calcula score sugerido;
- operador pode ajustar manualmente;
- ajuste manual deve registrar data e observação.

Escala padrão:

- 0 a 39: Frio;
- 40 a 69: Morno;
- 70 a 100: Quente.

Fatores de cálculo:

- origem;
- status no funil;
- atraso de follow-up;
- proposta aberta/enviada;
- valor/potencial;
- qualidade do contato;
- histórico de interações;
- template/nicho ativo.

---

## 12. Histórico e interações

O histórico deve registrar observações manuais e interações estruturadas.

Tipos mínimos:

- WhatsApp assistido;
- e-mail assistido;
- ligação registrada manualmente;
- reunião;
- proposta criada;
- proposta enviada;
- follow-up criado;
- status alterado;
- lead ganho;
- lead perdido;
- observação manual;
- anexo adicionado.

Cada interação deve registrar:

- data/hora;
- tipo;
- resumo;
- canal;
- próxima ação;
- data de follow-up, quando aplicável;
- status pendente/confirmado, quando for comunicação assistida.

---

## 13. WhatsApp assistido

O MVP deve permitir abrir WhatsApp Web/App com mensagem pré-preenchida.

Fluxo:

1. sistema gera ou monta mensagem sugerida;
2. operador clica em Abrir no WhatsApp;
3. sistema cria interação pendente no histórico;
4. WhatsApp Web/App abre com texto pré-preenchido;
5. operador revisa e envia manualmente;
6. operador confirma no OperIA CRM se enviou;
7. sistema atualiza histórico e follow-up.

Não haverá:

- disparo automático;
- envio em massa;
- WhatsApp API;
- robô conversando com cliente;
- confirmação automática de entrega/leitura.

---

## 14. E-mail assistido

O MVP deve permitir abrir cliente de e-mail padrão via mailto, com destinatário, assunto e corpo pré-preenchidos.

Fluxo equivalente ao WhatsApp:

- criar interação pendente;
- operador envia manualmente;
- operador confirma no CRM;
- sistema atualiza histórico e follow-up.

Não haverá SMTP próprio, Gmail API, Outlook API, campanha em massa ou rastreamento automático no MVP.

---

## 15. Follow-ups e agenda

O sistema deve ter duas camadas:

- agenda geral de follow-ups;
- follow-up dentro do lead/cliente.

Status padrão:

- Pendente;
- Concluído;
- Atrasado;
- Reagendado;
- Cancelado.

Alertas serão apenas internos, exibidos em:

- Cockpit Comercial;
- Agenda;
- Lead/Cliente;
- Propostas;
- PDF executivo.

Sem notificações externas no MVP.

---

## 16. Clientes

Lead ganho deve virar cliente.

Quando uma proposta for marcada como Ganha, o sistema deve sugerir conversão do lead em cliente.

A área de Clientes será simples:

- cadastro;
- histórico;
- propostas vinculadas;
- anexos;
- observações;
- próximos follow-ups;
- status do relacionamento.

Não entram no MVP:

- contratos recorrentes;
- financeiro;
- cobrança;
- emissão de boleto;
- helpdesk;
- SLA;
- chamados técnicos.

---

## 17. Propostas e orçamentos

Proposta/orçamento será entidade própria vinculada ao lead/cliente.

Status padrão:

- Aberta;
- Enviada;
- Ganha;
- Perdida;
- Cancelada.

Numeração automática:

- formato: PROP-0001;
- sequência por cliente;
- sem edição manual livre no MVP.

### PDF de proposta

O sistema deve gerar PDF simples de proposta.

Deve conter:

- dados da empresa emissora;
- logo, se configurado;
- dados do lead/cliente;
- número da proposta;
- data de emissão;
- validade;
- descrição livre opcional;
- lista de itens opcional;
- valor total;
- condições comerciais;
- observações;
- contato da empresa.

### Itens de proposta

Aceitar ambos os modos:

- descrição livre + valor total;
- lista de itens com descrição, quantidade, valor unitário e subtotal.

Não haverá no MVP:

- catálogo de produtos/serviços;
- desconto manual;
- campo próprio de forma de pagamento;
- assinatura digital;
- controle fiscal;
- financeiro;
- boleto;
- aprovação interna.

Condições comerciais e forma de pagamento ficam em campo textual.

Dados da empresa emissora serão configurados pela Biotech TI na implantação.

---

## 18. Anexos

O sistema deve permitir anexos simples ao lead/cliente.

Formatos permitidos:

- PDF;
- DOCX;
- XLSX;
- PNG;
- JPG/JPEG.

Não aceitar no MVP:

- EXE;
- BAT;
- CMD;
- PS1;
- JS;
- VBS;
- MSI;
- ZIP/RAR/7Z;
- arquivos desconhecidos.

Armazenamento recomendado:

- arquivos salvos em pasta local;
- banco guarda apenas caminho/metadados;
- backup inclui banco + anexos.

Metadados mínimos:

- nome original;
- nome salvo normalizado;
- extensão;
- tamanho;
- lead/cliente vinculado;
- data de inclusão;
- observação opcional.

---

## 19. Relatórios e exportações

O MVP deve entregar:

- CSV;
- Excel/XLSX, se viável;
- PDF executivo simples.

PDF executivo deve conter:

- resumo do período;
- leads por status;
- oportunidades quentes;
- follow-ups pendentes/atrasados;
- propostas abertas/enviadas;
- propostas ganhas/perdidas;
- valor potencial;
- ações recomendadas;
- resumo assistivo da IA.

Não exibir detalhes técnicos no relatório do cliente.

---

## 20. IA assistiva

Modelo híbrido:

1. regras locais primeiro;
2. Gemini quando configurado;
3. fallback local se API falhar;
4. operador humano revisa tudo.

Provider externo inicial:

- Gemini.

Gestão da chave:

- chave gerenciada pela Biotech TI; ou
- chave própria do cliente, conforme pacote.

IA deve apoiar:

- sugestão de mensagem WhatsApp;
- sugestão de e-mail;
- resumo do lead;
- próxima ação;
- classificação de prioridade;
- score assistivo;
- alerta de follow-up parado;
- adaptação por nicho.

IA não deve executar:

- disparo automático;
- decisão autônoma;
- atendimento automático ao cliente;
- scraping agressivo;
- enriquecimento massivo sem controle.

---

## 21. Banco de dados

MVP Local Managed:

- SQLite por cliente.

Futuro Hosted Managed / SaaS:

- PostgreSQL.

Diretriz de engenharia:

- evitar acoplamento rígido ao SQLite;
- isolar acesso a dados;
- preparar migração futura.

---

## 22. Backup

Modelo híbrido de responsabilidade:

- Biotech TI configura, orienta e valida;
- cliente mantém destino/mídia/conta de armazenamento;
- backup gerenciado pela Biotech pode ser pacote adicional.

Mínimo aceitável:

- backup diário do SQLite;
- backup da pasta de anexos;
- retenção local curta;
- cópia externa/cloud quando possível;
- teste periódico de restauração;
- log simples de sucesso/falha.

---

## 23. Segurança e acesso

MVP sem login forte.

Controle por:

- ambiente local;
- rede;
- firewall;
- usuário do sistema operacional;
- VPN quando necessário;
- permissões de pasta.

Sem expor:

- chaves API;
- tokens;
- caminhos internos sensíveis ao cliente;
- logs técnicos em relatório comercial.

`.env` local para segredos. Nunca versionar chaves.

---

## 24. Auditoria mínima

Registrar eventos:

- lead criado;
- lead atualizado;
- status alterado;
- score ajustado;
- proposta criada;
- PDF gerado;
- interação registrada;
- lead convertido em cliente;
- anexo adicionado;
- exportação gerada.

Sem auditoria por usuário no MVP, pois não haverá login forte.

---

## 25. Busca, tags e arquivamento

### Busca global

Pesquisar por:

- nome;
- empresa;
- telefone;
- e-mail;
- cidade;
- observação;
- status.

### Tags simples

Permitir tags como:

- quente;
- urgente;
- retomar depois;
- cliente estratégico;
- baixo potencial;
- aguardando retorno.

### Exclusão

Padrão: arquivar/inativar.

Exclusão definitiva apenas com confirmação forte e, preferencialmente, restrita à manutenção/admin.

---

## 26. Fora do escopo do MVP

Não implementar na primeira versão:

- login multiusuário forte;
- RBAC;
- responsável por lead;
- tarefas internas genéricas;
- calendário externo;
- notificações externas;
- WhatsApp API;
- envio automático de e-mail;
- campanhas em massa;
- scripts de ligação assistidos;
- catálogo de produtos/serviços;
- desconto manual;
- forma de pagamento estruturada;
- contratos/recorrência;
- financeiro;
- helpdesk;
- SaaS multiempresa completo.

---

## 27. Critérios de aceite do MVP

O MVP será considerado aderente quando permitir:

1. cadastrar lead rapidamente;
2. importar leads com validação e deduplicação;
3. visualizar Cockpit Comercial com ações do dia;
4. acompanhar funil simples;
5. registrar histórico estruturado;
6. criar follow-ups e agenda interna;
7. usar WhatsApp assistido com interação pendente;
8. usar e-mail assistido com interação pendente;
9. criar proposta/orçamento com numeração PROP-0001;
10. gerar PDF simples da proposta;
11. anexar documentos comerciais seguros ao lead/cliente;
12. converter lead ganho em cliente;
13. exportar CSV/Excel;
14. gerar PDF executivo simples;
15. usar score híbrido;
16. operar com fallback local de IA e Gemini opcional;
17. manter backup de banco e anexos;
18. evitar envio automático e automação cega.

---

## 28. Diretriz final

O OperIA CRM v1 deve ser simples, vendável, seguro e operacional.

O objetivo não é competir com Salesforce, ERP, helpdesk ou automação de marketing. O objetivo é resolver a dor real do pequeno negócio: organizar contatos, priorizar oportunidades, lembrar follow-ups, gerar propostas e manter histórico comercial.
