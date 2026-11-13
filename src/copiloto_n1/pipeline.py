from __future__ import annotations

from pathlib import Path

from copiloto_n1.extrator import ExtratorRegras
from copiloto_n1.perfil import carregar_perfil
from copiloto_n1.schemas import Chamado
from copiloto_n1.transcricao import transcrever
from copiloto_n1.validador import validar

_PERFIL = carregar_perfil("software_house")


def processar_audio(caminho_wav: str | Path):
    """Transcreve um áudio, extrai o chamado e valida a qualidade do atendimento."""
    resultado_transcricao = transcrever(caminho_wav)
    texto = resultado_transcricao.texto if hasattr(resultado_transcricao, "texto") else str(resultado_transcricao)

    # Sem identificação de falante, tratamos a transcrição como conversa única.
    # Não inventamos cliente/analista nem adicionamos labels artificiais.
    chamado = ExtratorRegras().extrair(texto)
    resultado_validacao = validar(chamado, _PERFIL)
    return resultado_transcricao, chamado, resultado_validacao
