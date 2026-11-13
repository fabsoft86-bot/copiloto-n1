# Backlog

Marque `[x]` ao concluir. Cada item tem critério de aceite curto; detalhes em `docs/PRD.md`.

## Fatia 1 — Validador (esqueleto entregue)

- [x] Schema `Chamado` (pydantic) e perfil YAML de software house/ERP
- [x] Validador com nota, pendências e perguntas sugeridas
- [x] CLI `validar` e `extrair`
- [x] Extrator por regras (CNPJ, telefone, e-mail, nome)
- [x] Adaptador de arquivo
- [x] Testes do validador, do perfil, do extrator e do adaptador

## Fatia 2 — Painel

- [ ] Painel Streamlit: colar conversa → ver campos extraídos, nota e pendências. *Aceite:* editar um campo recalcula a nota na hora.
- [ ] Botão "gerar chamado final". *Aceite:* gera texto com título, descrição, passos, evidências e solução.

## Fatia 3 — Extração por LLM

- [ ] `ExtratorLLM` com saída estruturada validada por pydantic. *Aceite:* extrai tipo, módulo, versão e descrição de 5 conversas fictícias.
- [ ] Sugestão da próxima pergunta. *Aceite:* sempre aponta uma pendência existente, nunca inventa campo.
- [ ] Aviso de classificação suspeita (descrição de erro marcada como dúvida) além do aviso por palavras-chave.

## Fatia 4 em diante

- [ ] Base de conhecimento local e busca de casos parecidos
- [ ] Rascunho de artigo KCS ao resolver
- [ ] Mascaramento de dados sensíveis
- [ ] Decisão local vs. nuvem para transcrição; captura de áudio
- [ ] Adaptador GLPI (API REST)
- [ ] Chatbot de autoatendimento

## Ideias soltas

- Perfil "TI interna" (ativo, usuário, setor) como segundo perfil
- Indicadores pessoais (tempo de resposta, FCR, reabertura)
