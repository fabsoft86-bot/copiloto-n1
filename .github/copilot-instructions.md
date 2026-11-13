# Instruções para o GitHub Copilot — Copiloto N1

Você implementa tarefas deste projeto. Leia `COPILOT.md`, `docs/PRD.md`, `docs/adr/` (principalmente o ADR-0003, PWA primeiro) e `docs/backlog.md` antes de propor mudanças. A interface oficial é um PWA; o Python é a especificação de referência.

## O projeto em uma frase

Copiloto para analista de suporte N1: lê a conversa de atendimento, preenche o chamado, valida a qualidade e sugere a próxima pergunta. O analista confirma tudo; nada é salvo ou enviado sem ação humana.

## Regras de arquitetura

- O **núcleo** (`schemas`, `perfil`, `validador`, `extrator`) **não conhece nenhum helpdesk**. Integrações ficam em `src/copiloto_n1/adaptadores/`, uma classe por helpdesk, herdando de `AdaptadorHelpdesk`.
- **Regras de negócio vivem no perfil YAML** (`src/copiloto_n1/perfis/`), não em `if` espalhados. Para mudar campos, pesos, perguntas ou SLA, edite o YAML.
- O produto é **sem LLM**, offline e com dados locais; não adicione dependência de áudio, nuvem ou LLM sem ADR novo.
- Use **pydantic v2** para dados externos (JSON, saída de LLM). Valide na borda.
- Extração automática **nunca sobrescreve** valor já preenchido pelo analista (use `mesclar`).

## Estilo

- Python 3.11+, type hints, `from __future__ import annotations`.
- Nomes de domínio em **português** (`chamado`, `pendencia`, `perfil`); identificadores técnicos genéricos em inglês quando forem convenção da linguagem.
- Mensagens ao usuário em **português do Brasil**, curtas e acionáveis.
- Funções pequenas e puras quando possível; sem estado global.

## Testes

- Toda mudança de comportamento vem com teste em `tests/` (pytest).
- Testes **não** podem depender de internet nem de chave de API. Use exemplos fictícios.
- Rode `pytest` antes de dizer que terminou.

## Privacidade e segurança

- Nunca coloque dados reais de clientes em exemplos, testes ou logs. Use nomes, CNPJs e telefones fictícios.
- Não persista áudio. Dados sensíveis (senhas, CPF, cartão) devem ser mascarados antes de gravar.
- Nunca commite chaves de API; use `.env` (ver `.env.example`).

## O que não fazer

- Não copiar textos de cursos ou materiais de terceiros para o repositório.
- Não criar chamadas externas silenciosas; toda integração é explícita e configurável.
- Não ampliar o escopo além do item do backlog que está sendo implementado.
