from __future__ import annotations

import io
import math

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from web.servidor import app


client = TestClient(app)


def _gerar_wav_tom() -> bytes:
    sample_rate = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False, dtype=np.float32)
    tone = 0.4 * np.sin(2 * np.pi * 440.0 * t).astype(np.float32)
    buffer = io.BytesIO()
    sf.write(buffer, tone, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def test_root_serves_placeholder() -> None:
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "ok" in resposta.text.lower()


def test_transcrever_endpoint() -> None:
    wav = _gerar_wav_tom()
    resposta = client.post(
        "/transcrever",
        files={"audio": ("teste.wav", wav, "audio/wav")},
    )
    assert resposta.status_code == 200, resposta.text
    payload = resposta.json()
    assert "texto" in payload
    assert "duracao_audio" in payload
    assert "segmentos" in payload
    assert "tempo_processamento" in payload
