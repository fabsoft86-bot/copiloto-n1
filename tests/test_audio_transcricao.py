from __future__ import annotations

import pytest

from copiloto_n1 import audio, transcricao


def test_audio_raises_when_sounddevice_missing(monkeypatch):
    monkeypatch.setattr(audio, "sd", None)
    with pytest.raises(RuntimeError, match="sounddevice"):
        audio.gravar_wav("teste.wav", segundos=0.1)


def test_listar_dispositivos_raises_when_dependency_missing(monkeypatch):
    monkeypatch.setattr(audio, "sd", None)
    with pytest.raises(RuntimeError, match="sounddevice"):
        audio.listar_dispositivos()


def test_transcricao_raises_when_faster_whisper_missing(monkeypatch):
    monkeypatch.setattr(transcricao, "WhisperModel", None)
    with pytest.raises(RuntimeError, match="faster-whisper"):
        transcricao.transcrever_arquivo("teste.wav")


def test_transcricao_usa_cache_e_segmentos(monkeypatch, tmp_path):
    class FakeSegment:
        def __init__(self, start, end, text):
            self.start = start
            self.end = end
            self.text = text

    class FakeModel:
        def __init__(self, model_name, device, compute_type):
            self.model_name = model_name
            self.device = device
            self.compute_type = compute_type

        def transcribe(self, path, language, beam_size, vad_filter):
            return [
                FakeSegment(0.0, 1.5, "Olá "),
                FakeSegment(1.5, 3.0, "mundo"),
                FakeSegment(3.0, 3.5, " "),
            ], {"language": language}

    monkeypatch.setattr(transcricao, "WhisperModel", FakeModel)
    transcricao._CACHE_MODELOS.clear()
    caminho = tmp_path / "teste.wav"
    caminho.write_bytes(b"fake wav")

    resultado = transcricao.transcrever(caminho, modelo="small", idioma="pt")

    assert resultado.texto == "Olá mundo"
    assert [segmento.text for segmento in resultado.segmentos] == ["Olá", "mundo"]
    assert len(transcricao._CACHE_MODELOS) == 1


def test_intercalar_segmentos_por_tempo():
    analista = [
        transcricao.SegmentoTranscricao(0.0, 1.2, "Bom dia, tudo certo?"),
        transcricao.SegmentoTranscricao(3.0, 4.0, "Vou verificar no sistema."),
    ]
    cliente = [
        transcricao.SegmentoTranscricao(1.1, 2.0, "Bom dia, preciso de ajuda."),
        transcricao.SegmentoTranscricao(4.1, 5.0, "A nota fiscal não abre."),
    ]

    intercalado = transcricao.intercalar_segmentos(analista, cliente)

    assert [item["rotulo"] for item in intercalado] == ["Analista", "Cliente", "Analista", "Cliente"]
    assert [item["texto"] for item in intercalado] == [
        "Bom dia, tudo certo?",
        "Bom dia, preciso de ajuda.",
        "Vou verificar no sistema.",
        "A nota fiscal não abre.",
    ]
    assert transcricao.formatar_conversa_intercalada(analista, cliente).startswith("Analista: Bom dia, tudo certo?")
