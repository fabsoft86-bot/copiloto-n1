import json
from pathlib import Path

import pytest

from copiloto_n1.perfil import carregar_perfil
from copiloto_n1.schemas import Chamado
from copiloto_n1.validador import cnpj_valido, condicao_atendida, proxima_pergunta, validar

EXEMPLOS = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture(scope="module")
def perfil():
    return carregar_perfil("software_house")


def _carregar(nome: str) -> Chamado:
    return Chamado.model_validate(json.loads((EXEMPLOS / nome).read_text(encoding="utf-8")))


def _campos(res):
    return {p.campo for p in res.pendencias}


# --- critérios de aceite do MVP -------------------------------------------------


def test_chamado_completo_aprova_com_nota_100(perfil):
    res = validar(_carregar("chamado_bom.json"), perfil)
    assert res.pendencias == []
    assert res.nota == 100
    assert res.aprovado
    assert res.sla_horas == 4


def test_chamado_ruim_reprova_com_pergunta_para_cada_pendencia(perfil):
    res = validar(_carregar("chamado_ruim.json"), perfil)
    assert not res.aprovado
    assert res.nota < 50
    assert res.pendencias
    assert all(p.pergunta for p in res.pendencias)
    assert proxima_pergunta(res) == res.pendencias[0].pergunta
    assert res.pendencias[0].severidade == "bloqueante"  # bloqueantes vêm primeiro


def test_cnpj_invalido_telefone_nao_confirmado_e_titulo_generico(perfil):
    c = Chamado(
        cnpj="11.111.111/1111-11",
        telefone="(11) 91234-5678",
        telefone_confirmado=False,
        titulo="problema",
    )
    problemas = {p.campo: p.problema for p in validar(c, perfil).pendencias}
    assert "CNPJ inválido" in problemas["cnpj"]
    assert "não confirmado" in problemas["telefone"]
    assert "genérico" in problemas["titulo"]


# --- condições por tipo e status ------------------------------------------------


def test_bug_exige_versao_evidencia_passos_e_base_de_teste(perfil):
    res = validar(Chamado(tipo="bug"), perfil)
    assert {"versao", "evidencias", "passos_reproducao", "reproduzido_base_teste"} <= _campos(res)


def test_duvida_nao_exige_campos_de_bug(perfil):
    res = validar(Chamado(tipo="duvida"), perfil)
    assert _campos(res).isdisjoint(
        {"versao", "evidencias", "passos_reproducao", "reproduzido_base_teste"}
    )


def test_resolvido_exige_solucao_e_escalado_exige_destino(perfil):
    assert "solucao" in _campos(validar(Chamado(status="resolvido"), perfil))
    assert "destino_escalonamento" not in _campos(validar(Chamado(status="resolvido"), perfil))
    assert "destino_escalonamento" in _campos(validar(Chamado(status="escalado"), perfil))
    assert "solucao" not in _campos(validar(Chamado(status="escalado"), perfil))


def test_chamado_aberto_nao_exige_desfecho(perfil):
    campos = _campos(validar(Chamado(), perfil))
    assert campos.isdisjoint({"solucao", "destino_escalonamento", "causa_raiz"})


# --- títulos, avisos, nota -------------------------------------------------------


@pytest.mark.parametrize("titulo", [".", "...", "123456", "ajuda", "erro", "erro no PDV"])
def test_titulos_ruins_geram_pendencia(perfil, titulo):
    assert "titulo" in _campos(validar(Chamado(titulo=titulo), perfil))


def test_titulo_bom_passa(perfil):
    c = Chamado(titulo="Erro ao emitir NFC-e no PDV após atualização")
    assert "titulo" not in _campos(validar(c, perfil))


def test_aviso_de_duvida_que_parece_bug(perfil):
    res = validar(Chamado(tipo="duvida", descricao="o sistema trava ao abrir o relatório"), perfil)
    assert any("bug" in a.lower() for a in res.avisos)


def test_sem_aviso_quando_duvida_e_realmente_duvida(perfil):
    res = validar(Chamado(tipo="duvida", descricao="onde cadastro um novo produto?"), perfil)
    assert res.avisos == []


def test_nota_fica_entre_0_e_100_e_chamado_vazio_reprova(perfil):
    res = validar(Chamado(), perfil)
    assert 0 <= res.nota <= 100
    assert not res.aprovado


def test_nota_sobe_ao_corrigir_pendencias(perfil):
    antes = validar(Chamado(), perfil).nota
    depois = validar(Chamado(contato_nome="Ana Lima", empresa="Loja Exemplo"), perfil).nota
    assert depois > antes


# --- utilitários -----------------------------------------------------------------


def test_cnpj_valido_e_invalido():
    assert cnpj_valido("11.222.333/0001-81")
    assert cnpj_valido("11222333000181")
    assert not cnpj_valido("11.222.333/0001-82")
    assert not cnpj_valido("00000000000000")
    assert not cnpj_valido("123")


def test_condicao_atendida():
    c = Chamado(tipo="bug", status="escalado")
    assert condicao_atendida("sempre", c)
    assert condicao_atendida("tipo=bug", c)
    assert condicao_atendida("status=resolvido|escalado", c)
    assert not condicao_atendida("tipo=duvida", c)
    with pytest.raises(ValueError):
        condicao_atendida("tipo", c)


def test_telefone_com_ddi_55_e_aceito(perfil):
    c = Chamado(telefone="+55 11 91234-5678", telefone_confirmado=True)
    assert "telefone" not in _campos(validar(c, perfil))


def test_json_com_campo_desconhecido_e_rejeitado():
    with pytest.raises(Exception):
        Chamado.model_validate({"titulo_do_chamado": "x"})
