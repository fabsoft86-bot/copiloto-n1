# Backlog

Marque `[x]` ao concluir. Uma etapa por vez; cada uma termina com um teste de aceite. Direção: PWA, sem LLM (ADR-0003).

## Feito (especificação de referência em Python)

- [x] Schema `Chamado`, perfil YAML de software house/ERP, validador com nota, pendências e perguntas
- [x] Extrator por regras (CNPJ, telefone, e-mail, nome), CLI, adaptador de arquivo, testes (67 passando)

## Etapa 1 — Roteiro guiado (PWA)

- [ ] Roteiro em dados (YAML/JSON) com ramificação por tipo: dúvida, erro, solicitação.
- [ ] Tela que mostra **uma pergunta por vez**, com respostas por clique ou campo curto.
- [ ] Validação na hora (CNPJ, telefone, e-mail), portada do `validador.py`.
- [ ] *Aceite:* rodar 3 atendimentos fictícios (um de cada tipo) do começo ao fim, sem erro.

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
