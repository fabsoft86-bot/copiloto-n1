from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("copiloto_n1.web")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / "web.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)

_MODEL = None


def _carregar_modelo() -> WhisperModel:
    global _MODEL
    if _MODEL is None:
        print("Carregando modelo faster-whisper small (pt)... isso pode levar alguns minutos.")
        _MODEL = WhisperModel(model_size_or_path="small", device="cpu", compute_type="int8")
    return _MODEL


app = FastAPI(title="copiloto-n1 web")
app.mount("/static", StaticFiles(directory=str(ROOT / "web" / "static")), name="static")


@app.get("/")
def raiz() -> FileResponse:
    return FileResponse(ROOT / "web" / "static" / "index.html")


@app.post("/transcrever")
async def transcrever(audio: UploadFile = File(...)) -> JSONResponse:
    inicio_total = time.monotonic()
    try:
        if not audio or not audio.filename:
            raise HTTPException(status_code=400, detail="Arquivo de áudio não enviado")

        extensao = Path(audio.filename).suffix.lower() or ".wav"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pasta = ROOT / "gravacoes"
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"{timestamp}{extensao}"

        dados = await audio.read()
        caminho.write_bytes(dados)

        inicio = time.monotonic()
        modelo = _carregar_modelo()
        segmentos, _info = modelo.transcribe(str(caminho), language="pt", task="transcribe", vad_filter=True)
        lista_segmentos = list(segmentos)
        texto = " ".join(seg.text.strip() for seg in lista_segmentos if str(seg.text or "").strip())
        tempo_proc = time.monotonic() - inicio
        tempo_total = time.monotonic() - inicio_total

        if not texto.strip():
            return JSONResponse(
                {
                    "texto": "",
                    "aviso": "Nenhuma fala detectada",
                    "duracao_audio": round((caminho.stat().st_size / 1024) / 8, 3),
                    "segmentos": 0,
                    "tempo_processamento": round(tempo_proc, 3),
                    "tempo_total": round(tempo_total, 3),
                }
            )

        return JSONResponse(
            {
                "texto": texto.strip(),
                "duracao_audio": round((caminho.stat().st_size / 1024) / 8, 3),
                "segmentos": len(lista_segmentos),
                "tempo_processamento": round(tempo_proc, 3),
                "tempo_total": round(tempo_total, 3),
            }
        )
    except Exception as exc:
        logger.exception("Erro ao transcrever áudio via web")
        mensagem = f"Erro ao transcrever arquivo: {type(exc).__name__}: {exc}"
        return JSONResponse(status_code=500, content={"erro": mensagem, "traceback": traceback.format_exc()})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
