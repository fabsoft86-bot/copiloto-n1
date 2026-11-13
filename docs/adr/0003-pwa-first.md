# ADR-0003 — PWA primeiro (substitui a direção "desktop first")

**Status:** aceito · **Data:** 2026-11-11 · **Substitui:** a diretriz "desktop nativo" do `COPILOT.md` anterior

## Contexto

O projeto caminhava para um app desktop (PySide6 + PyInstaller) e tinha também um painel Streamlit e um
protótipo web de microfone. Resultado: três interfaces para o mesmo produto, arquivos de mais de mil linhas
e empacotamento de `.exe` frágil. O produto foi redefinido como **assistente pessoal de atendimento N1,
sem LLM**: um roteiro guiado de perguntas que gera o texto final do chamado (ver ADR-0004 quando existir,
e `docs/PRD.md`).

## Decisão

A interface oficial é um **PWA** (Progressive Web App): HTML + JavaScript estáticos, instalável, que
funciona **offline** e guarda os dados **no próprio dispositivo** (IndexedDB/localStorage).

- **Sem backend** na primeira versão. Hospedagem estática (GitHub Pages ou similar), HTTPS.
- Roteiro de perguntas e regras de validação em **dados** (YAML/JSON), não em código.
- Saída principal: texto do chamado + botão **copiar**, para colar em qualquer helpdesk.
- Funciona em PC e celular com o mesmo código; sem instalador, sem `.exe`.

## Alternativas consideradas

- **Desktop (PySide6 + PyInstaller):** instalação e atualização manuais, build frágil, um sistema
  operacional por vez. Descartado.
- **Streamlit:** exige servidor Python rodando; sem offline; microfone instável. Descartado como produto.
- **PWA com backend Python (FastAPI):** útil só se surgir necessidade real (sincronizar entre
  dispositivos, integrações). Adiar até ser necessário.

## Consequências

- A lógica hoje em Python (validador, regras do perfil) precisa ser **reescrita em JavaScript**. O código
  Python e sua suíte de testes ficam como **especificação de referência** e fonte de casos de teste até a
  portagem terminar; depois decidimos se ficam ou saem.
- Código desktop arquivado em `legado/desktop/` (o histórico do Git preserva tudo).
- Microfone: `getUserMedia` funciona bem em PWA sobre HTTPS. Transcrição fica **opcional e posterior**.
  Atenção: a Web Speech API do navegador envia áudio a servidores do fornecedor (LGPD); transcrição
  local no navegador (Whisper em WebAssembly) é a alternativa e exige decisão própria.
- iOS tem limitações de PWA (armazenamento pode ser limpo se o app ficar sem uso). Por isso o app deve
  oferecer **exportar/importar** o histórico.
- Service worker exige cuidado com versões de cache a cada publicação.
