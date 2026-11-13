# Copiloto N1 — regras de projeto

## Visão do produto
- O projeto é um assistente de suporte N1 para analistas.
- A lógica principal de extração, validação e resumo do chamado deve ser preservada.
- A direção atual é desktop-first, com foco em um app nativo estável e útil, não em protótipos de browser.
- O app deve funcionar como ferramenta operacional para analistas, sem ruído excessivo nem UX confusa.

## Regras de implementação
- Não quebrar o fluxo principal do chamado: extrair -> validar -> sugerir próxima pergunta -> resumir.
- Sempre preservar o modelo neutro do chamado (`Chamado`) e a lógica de domínio.
- Não reescrever a base funcional para trocar de caminho sem necessidade.
- Priorizar estabilidade e confiabilidade sobre "novidades" visuais ou arquiteturais.
- Qualquer mudança em extração, validação ou exportação precisa ser testada.

## Desktop e packaging
- A aplicação oficial é a versão desktop nativa.
- O arquivo principal de app é `src/copiloto_n1/desktop_app.py`.
- O build de executável usa `build_exe.py` via PyInstaller.
- Quando mexer no empacotamento, considerar conflitos de lock do `.exe` e remover builds antigos antes de recriar.
- O executável deve abrir como app desktop, não como CLI/Streamlit.

## UX e produto
- O app deve ser claro, limpo e focado em operação.
- Evitar excesso de botões, labels confusas e blocos visuais duplicados.
- Dar prioridade a fluxo de analista: conversa, extração, validação, resumo final.
- A tela deve ser funcional, legível e de aparência profissional.

## Microfone / transcrição
- O uso de microfone em browser/Streamlit não é confiável como solução final.
- Não tratar o problema como um ajuste marginal de UI; considerar arquitetura real do desktop.
- O fluxo de gravação/transcrição deve ser simples e seguro.
- Se a transcrição for implementada, ela deve integrar ao fluxo sem exigir cópia manual.

## Testes e validação
- Rodar pytest antes de concluir alterações relevantes.
- Quando mexer em build/package, validar o executável também.
- Se uma correção mexe em comportamento funcional, verificar o impacto nos testes.

## Estrutura relevante
- `src/copiloto_n1/desktop_app.py` — app desktop principal
- `src/copiloto_n1/cli.py` — entrypoints e comandos
- `src/copiloto_n1/extrator.py` — extração da conversa
- `src/copiloto_n1/validador.py` — validação e qualidade
- `src/copiloto_n1/schemas.py` — modelo central do chamado
- `build_exe.py` — geração do executável
- `tests/` — suíte de regressão

## Boas práticas para o agente
- Seja preciso e não faça refactor grande sem necessidade.
- Corrija a causa raiz, não apenas o sintoma.
- Evite trabalhar em múltiplas frentes ao mesmo tempo quando o objetivo é uma correção pontual.
- Preserve comportamento existente que já está validado.
- Se houver uma falha real de runtime, priorizar estabilidade do app antes de refinamento visual.

## Resumo executivo
- App funcional e estável primeiro.
- Produto polido segundo.
- Logica de negócio preservada.
- Desktop como caminho principal.
- Validação contínua por testes e build.
