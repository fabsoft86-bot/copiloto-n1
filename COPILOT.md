# Copiloto N1 — regras de projeto

## Visão do produto
- Assistente **pessoal** do analista de suporte N1: um **roteiro guiado de perguntas** que conduz o
  atendimento, valida o que falta e gera o texto final do chamado. **Sem LLM**, offline, dados locais.
- A decisão de plataforma está em `docs/adr/0003-pwa-first.md`: **PWA primeiro**.
- O analista continua no controle: o app sugere, o humano confirma. Nada é enviado sem ação humana.
- Critério de sobrevivência do projeto: se, após uma semana de uso em atendimentos reais, ele não
  economizar tempo ou evitar esquecimentos, abandonamos e escolhemos outro projeto.

## Regras de implementação
- Fatias pequenas e testadas. Uma etapa por vez; só avançar com a anterior funcionando.
- Roteiro, perguntas, pesos e SLA vivem em **dados** (perfil YAML/JSON), não em código.
- Priorizar estabilidade e simplicidade sobre novidades.
- Toda mudança de regra de extração, validação ou geração de texto precisa de teste.

## PWA
- HTML/CSS/JS estáticos, sem backend na v1; instalável e offline (service worker).
- Dados no dispositivo (IndexedDB/localStorage). Oferecer **exportar/importar** o histórico.
- Saída principal: texto formatado + botão copiar. Integração com helpdesk só depois de provar valor.
- Ao publicar uma versão nova, mudar a versão do cache do service worker.
- Microfone/transcrição é opcional e posterior (ver riscos de LGPD no ADR-0003).

## Código Python existente
- `src/copiloto_n1/` (schemas, perfil, validador, extrator, adaptadores, CLI) e `tests/` são a
  **especificação de referência** das regras. Ao portar para JS, reaproveitar os casos de teste.
- `legado/desktop/` guarda o app PySide6 e o build do `.exe`. Não evoluir; só consultar.
- O painel Streamlit (`painel.py`) é legado e sai quando o PWA cobrir o mesmo fluxo.
- `experimentos/web_mic/` é um protótipo arquivado de microfone no navegador.

## UX e produto
- Uma pergunta por vez, a próxima depende da resposta anterior; cliques antes de digitação.
- Tela limpa, legível, focada no fluxo: perguntar → registrar → conferir → copiar.

## Testes e validação
- Rodar `pytest` (regras de referência em Python) antes de concluir mudanças no núcleo Python.
- No PWA, cada etapa tem um teste de aceite descrito em `docs/backlog.md`.

## Privacidade
- Dados de clientes ficam no dispositivo. Nunca versionar áudio, históricos ou `.env`.
- Exemplos e testes só com dados fictícios.
