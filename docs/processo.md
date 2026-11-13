# Como trabalhamos

## Método

**Kanban leve com fatias verticais.** Projeto solo não precisa de Scrum completo. Cada entrega atravessa o sistema inteiro (conversa → campos → validação → registro), mesmo que simples.

- Quadro: `Backlog → Fazendo (máx. 2) → Revisão → Feito`.
- **Definição de pronto:** código com testes passando, critério de aceite verificado, documentação atualizada (PRD/ADR se a decisão mudou).
- Decisões de arquitetura importantes viram um **ADR** curto em `docs/adr/`.

## "Time de IAs" = chapéus com âncoras objetivas

Várias IAs podem ajudar, mas elas só se monitoram bem quando há **âncoras objetivas**; sem isso, uma valida o erro da outra com confiança.

| Chapéu | Quem | O que faz |
|---|---|---|
| Dono do produto | Você | Decide escopo e prioridade, aprova critérios de aceite |
| Consultor de produto/arquitetura | Claude (chat) | Discute alternativas, escreve PRD/ADR, revisa o plano |
| Programador | GitHub Copilot no VS Code | Implementa a tarefa seguindo `.github/copilot-instructions.md` |
| Revisor | Sessão **limpa** de IA (sem ter visto o código sendo escrito) | Revisa cada mudança contra o critério de aceite |

Âncoras:

1. **Fonte única da verdade no repositório:** PRD, ADRs e backlog. Qualquer IA lê dali, não de memória de conversa.
2. **Testes automatizados como juiz:** nenhuma tarefa está pronta sem `pytest` verde.
3. **Humano decide:** divergência entre IAs vai para você.

## Fluxo de uma tarefa

1. Escolher um item do `docs/backlog.md` e copiar o critério de aceite.
2. Pedir ao Copilot a implementação, citando o item e os arquivos envolvidos.
3. Rodar `pytest` e a CLI nos exemplos.
4. Pedir revisão a uma sessão limpa, passando só o diff e o critério de aceite.
5. Atualizar docs, mover o cartão para Feito.
