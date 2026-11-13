# ADR-0001 — Aplicativo companheiro (sidecar) com adaptadores de helpdesk

**Status:** aceito · **Data:** 2026-10-16

## Contexto

O copiloto deve ajudar o analista N1 sem ser um helpdesk. Existem várias opções: fork de um helpdesk open source, plugin dentro de um helpdesk, ou um aplicativo à parte que conversa com o helpdesk pela API.

## Decisão

Construir um **aplicativo companheiro (sidecar) em Python** com um **núcleo neutro** (schemas, perfil, validador, extração, sugestões) e **adaptadores** finos para cada helpdesk. O primeiro adaptador grava em arquivo; o primeiro helpdesk real será o **GLPI** (open source, com API REST).

## Alternativas consideradas

- **Fork de helpdesk open source:** herda manutenção do projeto inteiro (atualizações, segurança) e obrigações de licença GPL/AGPL. Muito custo para pouco ganho.
- **Plugin dentro do helpdesk:** prende a linguagem e o ciclo de versões do produto hospedeiro, e captura de áudio em tempo real não combina com rodar dentro de uma página.

## Consequências

- O núcleo funciona sem helpdesk (modo arquivo) e é testável offline.
- Adicionar Zammad, Zendesk ou Freshdesk = escrever um adaptador novo, sem mexer no núcleo.
- É preciso manter o mapeamento de campos entre o `Chamado` interno e cada helpdesk.
