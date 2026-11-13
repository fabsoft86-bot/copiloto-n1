# Proposta comercial do Copiloto N1

## Resumo executivo
O Copiloto N1 é um assistente de triagem e validação para analistas de suporte N1. Ele transforma a conversa do cliente em um chamado estruturado, identifica pendências, sugere a próxima pergunta e reduz retrabalho antes do escalonamento.

A proposta de valor não é substituir o analista, e sim tirar de cima dele a parte mais repetitiva e propensa a erro: registrar, validar e organizar a informação de forma consistente.

## O problema que ele resolve
Em times de suporte, a etapa de N1 costuma ser a mais intensa em volume e mais vulnerável a falhas de qualidade:

- conversas caóticas e incompletas
- informações espalhadas entre e-mail, chat e telefone
- ticket com dados faltantes ou mal organizados
- necessidade de repetir perguntas para completar o caso
- risco de escalonamento tardio ou incorreto
- pressão por SLA e produtividade

## A solução
O Copiloto N1 atua como um copiloto do analista:

- lê a conversa do atendimento
- extrai campos relevantes
- calcula uma nota de qualidade do chamado
- aponta pendências e riscos
- sugere a pergunta correta para completar o registro
- exporta para JSON, TXT ou integra com GLPI/Jira

## Valor para o cliente
### Para o time de suporte
- menos retrabalho
- menos ambiguidades no registro
- chamada de atenção mais clara para pendências
- triagem mais rápida e mais consistente

### Para a operação
- melhor qualidade na entrada de chamados
- redução de escalonamentos equivocados
- melhor aproveitamento do analista
- mais previsibilidade e menos tensão na fila

### Para a empresa
- ganho de produtividade em escala
- melhoria de SLA e qualidade do atendimento
- mais visibilidade sobre o que está faltando no processo
- base para evoluir para automação e analytics

## Posicionamento de mercado
O produto se encaixa na categoria de ajuda operacional para suporte, ao lado de soluções de helpdesk e automação de atendimento, mas com um foco mais específico:

- não é um CRM completo
- não é um helpdesk substituto
- é um copiloto de qualidade e triagem, com visão humana no centro do fluxo

Isso torna a solução mais simples de adotar, mais barata de começar e mais fácil de integrar a sistemas existentes.

## Cenários de uso
### 1. Suporte de software e ERP
Analistas recebem dezenas de tickets com linguagem improvisada e dados incompletos. O Copiloto N1 ajuda a transformar isso em ticket revisado e pronto para encaminhamento.

### 2. Atendimento em volume
Quando o volume aumenta, o risco de inconsistência na coleta de dados cresce. O sistema ajuda a padronizar um ponto crítico do processo.

### 3. Operação com integrações
A solução já é útil como camada local de revisão e pode evoluir para integração nativa com GLPI, Jira, Zendesk ou outros sistemas.

## Modelo de negócio sugerido
### Opção 1: assinatura por usuário
- melhor para empresas com poucos analistas ou times de suporte distribuídos
- preço mais simples de vender e dimensionar

### Opção 2: assinatura por time / operação
- melhor para departamentos de suporte maiores
- permite cobrança por número de analistas ou por SLA da operação

### Opção 3: pacote com integração e customização
- inclui setup, regras de validação e integrações com helpdesk
- mais adequado para empresas que querem uma solução ajustada ao processo

## Indicadores de valor
Sem necessidade de métricas complexas, os primeiros sinais de sucesso podem ser:

- redução de chamados incompletos
- redução de perguntas repetidas
- tempo médio de registro por ticket
- taxa de escalonamento com informação completa
- satisfação do time de suporte

## Roadmap de evolução
### Fase 1 — MVP funcional
- extração por regras
- validação por nota e pendências
- painel visual e edição dinâmica
- exportação em JSON/TXT

### Fase 2 — IA e produtividade
- extração por LLM
- classificação mais inteligente
- sugestões contextualizadas de próxima pergunta
- melhor parsing de conversas complexas

### Fase 3 — integração operacional
- GLPI/Jira e outros helpdesks
- workflow de envio e rastreio
- histórico e métricas de qualidade

### Fase 4 — escala e analytics
- dashboards de produtividade
- modelos por perfil de cliente
- automação de triagem e priorização

## Mensagem final para apresentação
"O Copiloto N1 não substitui o analista; ele elimina a parte repetitiva e frágil do trabalho, deixando o suporte mais rápido, mais consistente e melhor preparado para tomar decisões."
