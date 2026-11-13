from __future__ import annotations

import numpy as np

from copiloto_n1 import audio


def test_reamostragem_para_16000_hz() -> None:
    origem = np.linspace(-1.0, 1.0, 8000, dtype=np.float32)
    reamostrado = audio.reamostrar_audio(origem, 8000, 16000)

    assert reamostrado.dtype == np.float32
    assert reamostrado.size == 16000
    assert np.isfinite(reamostrado).all()


def test_audio_mudo_retorna_true_quando_pico_baixo() -> None:
    sinal = np.array([0.001, -0.005, 0.002], dtype=np.float32)
    assert audio.audio_mudo(sinal, limite=0.01) is True


def test_audio_mudo_retorna_false_quando_pico_alto() -> None:
    sinal = np.array([0.0, 0.2, -0.08], dtype=np.float32)
    assert audio.audio_mudo(sinal, limite=0.01) is False
