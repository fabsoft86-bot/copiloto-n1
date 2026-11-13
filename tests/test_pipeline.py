from __future__ import annotations

from pathlib import Path

from copiloto_n1 import pipeline


def test_processar_audio_extrai_campos_principais(monkeypatch, tmp_path):
    texto = (
        "Cliente: Meu nome é Maria Souza.\n"
        "Cliente: Meu e-mail é maria@empresa.com.br.\n"
        "Cliente: Meu telefone é (11) 99999-1234.\n"
        "Cliente: Meu CNPJ é 12.345.678/0001-99.\n"
        "Cliente: Não consigo emitir nota fiscal no módulo de faturamento do ERP."
    )

    class FakeResultadoTranscricao:
        def __init__(self, texto: str):
            self.texto = texto

    monkeypatch.setattr(pipeline, "transcrever", lambda caminho_wav, **kwargs: FakeResultadoTranscricao(texto))

    caminho = tmp_path / "audio.wav"
    caminho.write_bytes(b"fake wav")

    transcricao_resultado, chamado, validacao = pipeline.processar_audio(caminho)

    assert transcricao_resultado.texto == texto
    assert chamado.contato_nome == "Maria Souza"
    assert chamado.email == "maria@empresa.com.br"
    assert chamado.telefone == "(11) 99999-1234"
    assert chamado.cnpj == "12.345.678/0001-99"
    assert validacao is not None
    assert hasattr(validacao, "nota")
