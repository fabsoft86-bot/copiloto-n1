# Copiloto N1
## Pitch de apresentação

---

## Slide 1 — O problema que estamos resolvendo

Suporte N1 vive em volume alto, dados incompletos e pressão por SLA.

- Conversas do cliente cheias de informações espalhadas
- Ticket sai incompleto ou ambíguo
- Analista repete perguntas e perde tempo
- Escalonamento acontece tarde ou com base fraca
- Resultado: retrabalho, risco operacional e qualidade instável

> O problema não é a falta de esforço do time — é a falta de estrutura e apoio na entrada do chamado.

---

## Slide 2 — A ideia

O Copiloto N1 ajuda o analista a transformar uma conversa em um chamado pronto para revisão e envio.

Ele:
- lê a conversa do atendimento
- extrai os dados relevantes
- valida a qualidade do chamado
- aponta pendências
- sugere a próxima pergunta
- exporta para JSON, TXT ou ajuda a enviar para GLPI/Jira

---

## Slide 3 — O que o produto faz

### Fluxo principal
1. O analista coleta a conversa
2. O sistema extrai campos do chamado
3. A ferramenta valida qualidade e pendências
4. O usuário edita e confirma
5. O chamado é exportado, salvo ou enviado para o helpdesk

### Resultado esperado
- menos retrabalho
- ticket melhor preenchido
- melhor qualidade antes do escalonamento
- analista mais rápido e mais seguro

---

## Slide 4 — Diferencial do Copiloto N1

### O que o torna relevante
- foco em N1 e triagem operacional
- qualidade explicável, não “caixa preta”
- revisão humana no centro do processo
- interface simples e rasa de adoção
- arquitetura pronta para evoluir com LLM e integrações

### Em uma frase
Não substitui o analista. Ele reduz a carga operacional e aumenta a qualidade de cada chamado.

---

## Slide 5 — Como funciona na prática

### Exemplo de uso
- conversa do cliente chega pelo chat ou telefone
- sistema extrai nome, CNPJ, e-mail, telefone, descrição e contexto
- valida nota e mostra pendências
- o analista confirma ou corrige
- resumo é copiado, salvo ou enviado para o backend

### Valor percebido
- tempo de registro menor
- menos erro humano
- menor risco de escalonamento frágil
- operação mais organizada

---

## Slide 6 — Demonstração do MVP

### O que já está funcionando
- painel Streamlit com UX orientada ao analista
- extração por regras e fallback inteligente
- nota de qualidade e severidade visual
- import/export JSON/TXT
- modo demo com cenários fictícios
- integração inicial com GLPI/Jira

### Demo em 5 minutos
- abrir painel
- carregar cenário demo
- revisar dados
- editar um campo
- observar recalculo em tempo real
- exportar resumo

---

## Slide 7 — Valor de negócio

### Para o time de suporte
- menos retrabalho
- menos perguntas repetidas
- tickets mais completos
- processo mais fluido

### Para a operação
- melhor qualidade de entrada
- redução de escalonamentos ruins
- melhor aproveitamento do analista
- mais previsibilidade de SLA

### Para a empresa
- produtividade em escala
- melhor experiência do cliente
- base para automatizar e evoluir a operação

---

## Slide 8 — Modelo de negócio sugerido

### Opção 1: assinatura por usuário
- ideal para times menores e iniciais
- fácil de testar e vender

### Opção 2: assinatura por time
- melhor para operação de suporte em volume
- escala com o número de analistas

### Opção 3: pacote com integração e customização
- inclui setup e adaptações de campo e workflow
- maior valor percebido e maior ticket médio

---

## Slide 9 — Roadmap

### Fase atual: MVP
- painel funcional
- extração e validação
- demo e exportação
- integração inicial com GLPI/Jira

### Próximas fases
- extração por LLM com maior precisão
- histórico de chamados e métricas
- dashboards de produtividade e SLA
- automação de triagem e priorização

---

## Slide 10 — Mensagem final

### O Copiloto N1 não substitui o analista.
Ele remove o peso do trabalho manual e deixa o time mais rápido, mais organizado e mais eficaz.

> Em vez de perder tempo montando o chamado, o analista foca no que realmente importa: entender o problema e resolver com qualidade.

---

## Fechamento para apresentação

"Hoje o projeto já funciona como MVP demonstrável, com valor claro para suporte N1, arquitetura preparada para crescimento e narrativa forte para venda ou apresentação interna."

### Pergunta de fechamento
- Você acha que este produto resolve um problema real e recorrente na operação de suporte?
- Se sim, qual seria a próxima etapa ideal: validação interna, integração em produção ou apresentação comercial?
