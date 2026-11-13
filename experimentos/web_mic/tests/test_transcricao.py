from __future__ import annotations

from copiloto_n1 import transcricao


class FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeModel:
    def __init__(self, *args, **kwargs) -> None:
        self.calls = []

    def transcribe(self, caminho, language=None, vad_filter=None):
        self.calls.append({"caminho": caminho, "language": language, "vad_filter": vad_filter})
        return [FakeSegment("teste de gravação"), FakeSegment("continuação")], None


def test_transcrever_reutiliza_modelo_ja_carregado(monkeypatch, tmp_path) -> None:
    arquivo = tmp_path / "teste.wav"
    arquivo.write_bytes(b"fake")

    created = []
    original_model = transcricao.WhisperModel
    original_cache = transcricao._MODELO
    transcricao._MODELO = None

    def fake_factory(*args, **kwargs):
        created.append((args, kwargs))
        return FakeModel()

    monkeypatch.setattr(transcricao, "WhisperModel", fake_factory)

    texto1 = transcricao.transcrever(arquivo, modelo="small", idioma="pt")
    texto2 = transcricao.transcrever(arquivo, modelo="small", idioma="pt")

    assert texto1 == "teste de gravação continuação"
    assert texto2 == texto1
    assert len(created) == 1

    transcricao.WhisperModel = original_model
    transcricao._MODELO = original_cache


def test_transcrever_reporta_erro_claro_se_arquivo_nao_existe() -> None:
    try:
        transcricao.transcrever("arquivo_inexistente.wav")
    except FileNotFoundError as exc:
        assert "Arquivo de áudio não encontrado" in str(exc)
    else:
        raise AssertionError("FileNotFoundError esperado")
