# Experimento: microfone no navegador (FastAPI)

Protótipo arquivado. Grava áudio no navegador e transcreve com faster-whisper.

**Status:** não é o caminho oficial. O `COPILOT.md` registra que microfone em navegador não é
confiável como solução final; a direção é o app desktop em `src/copiloto_n1/desktop_app.py`.
Mantido só como referência. Não faz parte da suíte principal (`pytest` na raiz ignora esta pasta).

Rodar (a partir desta pasta, com as dependências de `requirements.txt`):

```powershell
python -m uvicorn web.servidor:app --port 8000
```
