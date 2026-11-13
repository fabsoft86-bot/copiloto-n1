# Backlog

Marque `[x]` ao concluir. Uma etapa por vez; cada uma termina com um teste de aceite. Direção: PWA, sem LLM (ADR-0003).

## Feito (especificação de referência em Python)

- [x] Schema `Chamado`, perfil YAML de software house/ERP, validador com nota, pendências e perguntas
- [x] Extrator por regras (CNPJ, telefone, e-mail, nome), CLI, adaptador de arquivo, testes (67 passando)

## Etapa 1 — Roteiro guiado (PWA)

- [x] Roteiro em dados (`pwa/perfis/software_house.json`, gerado do YAML) com ramificação por tipo e situação.
- [x] Tela que mostra **uma pergunta por vez**, com respostas por clique ou campo curto, voltar, pular e editar.
- [x] Validação na hora (CNPJ, telefone, e-mail, título), portada do `validador.py` e conferida contra 345 casos gerados pelo Python.
- [x] *Aceite:* 3 atendimentos fictícios (dúvida, erro, melhoria) do começo ao fim em `pwa/tests/roteiro.test.js`; atendimento de erro também executado na tela, no Edge, com nota 100.
- [ ] Pendente da Etapa 1: testar a tela no celular e com leitor de tela; CI rodando `pytest` e `node --test`.

## Etapa 2 — Texto final e copiar

- [ ] Gerar o texto do chamado (título, descrição, passos, evidências, solução) a partir das respostas.
- [ ] Botão **copiar**.
- [ ] *Aceite:* colar o resultado no helpdesk real e achar que ficou bom. Começar o **teste de uma semana** em atendimentos reais.

## Etapa 3 — PWA instalável e histórico local

- [ ] Manifest + service worker (offline) com versão de cache.
- [ ] Histórico no dispositivo (IndexedDB), busca simples, exportar/importar.
- [ ] *Aceite:* instalar no celular e no PC, usar sem internet, exportar e reimportar o histórico.

## Etapa 4 — Opcional

- [ ] Microfone e transcrição (decidir local vs. nuvem antes; LGPD) e pré-preenchimento por regras.
- [ ] Integração com helpdesk (só se as etapas anteriores provarem valor).

## Limpeza

- [ ] Remover o painel Streamlit quando o PWA cobrir o fluxo.
- [ ] Remover o `ExtratorLLM` com fallback de palavras-chave (produto é sem LLM).
- [ ] Decidir o destino do núcleo Python depois da portagem (manter como referência ou remover).

## Critério de decisão (fim da Etapa 2)

Após uma semana de uso real: economizou tempo ou evitou esquecimentos? Abri o app por vontade própria? Se não, abandonar e escolher outro projeto.
