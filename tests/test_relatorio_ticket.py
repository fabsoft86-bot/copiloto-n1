from __future__ import annotations

import json

from copiloto_n1.desktop_app import salvar_atendimento_historico
from copiloto_n1.schemas import Chamado, gerar_relatorio_ticket
from copiloto_n1.validador import Pendencia, Resultado


def test_gerar_relatorio_ticket_usa_nao_informado_e_pendencias():
    chamado = Chamado(
        contato_nome="Maria",
        empresa=None,
        cnpj=None,
        telefone=None,
        email=None,
        titulo="Não consigo emitir nota fiscal",
        tipo="bug",
        prioridade=None,
        status="aberto",
        descricao="Ao clicar em emitir nota fiscal, o sistema trava.",
        modulo=None,
        versao=None,
        passos_reproducao=[],
        evidencias=[],
    )
    validacao = Resultado(
        nota=40,
        pendencias=[
            Pendencia(
                campo="empresa",
                rotulo="Empresa",
                severidade="bloqueante",
                problema="não informado",
                pergunta="Qual é o nome da empresa?",
            )
        ],
    )

    relatorio = gerar_relatorio_ticket(chamado, validacao)

    assert "Solicitante" in relatorio
    assert "Nome: Maria" in relatorio
    assert "Empresa: NÃO INFORMADO" in relatorio
    assert "Telefone: NÃO INFORMADO" in relatorio
    assert "Resumo do problema" in relatorio
    assert "Próximo passo / pendências" in relatorio
    assert "Empresa: Qual é o nome da empresa?" in relatorio


def test_salvar_atendimento_historico_cria_json(tmp_path):
    chamado = Chamado(
        contato_nome="João",
        titulo="Erro ao emitir NF",
        tipo="bug",
        status="aberto",
        descricao="Erro ao emitir nota fiscal.",
    )

    caminho = salvar_atendimento_historico(
        chamado,
        transcricao="Cliente: Não consigo emitir nota fiscal.",
        relatorio="Resumo do problema\nNÃO INFORMADO",
        base_dir=tmp_path,
    )

    assert caminho.exists()
    payload = json.loads(caminho.read_text(encoding="utf-8"))
    assert payload["transcricao"] == "Cliente: Não consigo emitir nota fiscal."
    assert payload["relatorio"] == "Resumo do problema\nNÃO INFORMADO"
    assert payload["chamado"]["contato_nome"] == "João"
