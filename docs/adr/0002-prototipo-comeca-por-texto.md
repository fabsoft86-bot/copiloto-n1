# ADR-0002 — O protótipo começa por texto, não por áudio

**Status:** aceito · **Data:** 2026-10-16

## Contexto

A visão final inclui voz via headset com transcrição em tempo real. Mas o diferencial do produto (extração de campos e validador de qualidade) não depende de áudio, e áudio traz riscos: qualidade da transcrição em português, latência, identificação de quem fala e LGPD.

## Decisão

As primeiras fatias recebem a **conversa já em texto** (arquivo ou colada), no formato `Analista:` / `Cliente:`. O áudio entra em uma fatia posterior, como **mais uma fonte** que alimenta o mesmo pipeline.

## Consequências

- Validamos primeiro o que gera valor (extração + validador + painel) com custo e risco baixos.
- Dá para testar tudo offline e com conversas fictícias.
- A interface do pipeline não deve assumir que o texto veio de áudio (aceitar texto incompleto ou com erros de transcrição).
- A decisão de transcrição local vs. nuvem e a política de LGPD ficam para antes da fatia de áudio.
