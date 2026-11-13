import textwrap

import pytest

from copiloto_n1.perfil import carregar_perfil
from copiloto_n1.schemas import Chamado
from copiloto_n1.validador import validar


def test_perfil_embutido_carrega():
    perfil = carregar_perfil("software_house")
    assert perfil.nome == "software_house"
    assert perfil.sla_horas["alta"] == 4
    ids = [c.id for c in perfil.campos]
    assert len(ids) == len(set(ids)), "ids de campo devem ser únicos"
    assert {"contato_nome", "titulo", "tipo", "solucao"} <= set(ids)


def test_perfil_inexistente_da_erro_claro():
    with pytest.raises(FileNotFoundError):
        carregar_perfil("nao_existe")


def test_trocar_perfil_muda_as_regras_sem_mexer_no_codigo(tmp_path):
    yaml_minimo = textwrap.dedent(
        """
        nome: so_titulo
        campos:
          - id: titulo
            rotulo: Título
            peso: 10
            severidade: bloqueante
            validador: titulo
            pergunta: "Resuma o problema."
        """
    )
    arquivo = tmp_path / "so_titulo.yaml"
    arquivo.write_text(yaml_minimo, encoding="utf-8")
    perfil = carregar_perfil(arquivo)

    res = validar(Chamado(titulo="Erro ao emitir NFC-e no PDV hoje"), perfil)
    assert res.nota == 100 and res.aprovado  # mesmo sem nome, empresa etc.


@pytest.mark.parametrize(
    "trecho, mensagem",
    [
        ("severidade: urgente", "severidade"),
        ("validador: inventado", "validador"),
        ("peso: 0", "peso"),
    ],
)
def test_perfil_invalido_e_rejeitado(tmp_path, trecho, mensagem):
    base = {"severidade": "bloqueante", "validador": "presenca", "peso": "5"}
    chave, _, valor = trecho.partition(": ")
    base[chave] = valor
    yaml_ruim = (
        "campos:\n"
        "  - id: x\n    rotulo: X\n    pergunta: \"?\"\n"
        f"    peso: {base['peso']}\n    severidade: {base['severidade']}\n"
        f"    validador: {base['validador']}\n"
    )
    arquivo = tmp_path / "ruim.yaml"
    arquivo.write_text(yaml_ruim, encoding="utf-8")
    with pytest.raises(ValueError, match=mensagem):
        carregar_perfil(arquivo)
