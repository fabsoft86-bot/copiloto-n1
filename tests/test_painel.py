import json

from copiloto_n1.painel import (
    DEMO_CENARIOS,
    abrir_configuracoes_microfone,
    carregar_chamado_json,
    carregar_chamado_txt,
    carregar_demo,
    classificar_severidade_por_nota,
    filtrar_historico,
    gerar_chamado_final_painel,
    guia_microfone_iniciante,
    historico_a_partir_de_chamado,
    resumo_demo_narrativa,
    resumo_texto_limpo,
    salvar_chamado_json,
    salvar_chamado_txt,
    sugestoes_do_assistente,
)
from copiloto_n1.schemas import Chamado


def test_classificacao_por_nota_mapeia_severidade():
    assert classificar_severidade_por_nota(15) == "alta"
    assert classificar_severidade_por_nota(60) == "media"
    assert classificar_severidade_por_nota(90) == "baixa"


def test_resumo_texto_limpo_remove_linhas_vazias():
    chamado = Chamado(
        titulo="Erro ao emitir NFC-e no PDV",
        tipo="bug",
        descricao="Ao clicar em emitir, o sistema trava.",
        passos_reproducao=["Abre o PDV", "Clica em emitir"],
        evidencias=["print_001.png"],
        solucao="Reinstalei a biblioteca de NFC-e.",
    )
    resumo = resumo_texto_limpo(chamado)
    assert "Título: Erro ao emitir NFC-e no PDV" in resumo
    assert "Ao clicar em emitir, o sistema trava." in resumo
    assert "Passos para reprodução" in resumo
    assert "\n\n" not in resumo


def test_salvar_e_carregar_json_do_chamado_roundtrip(tmp_path):
    chamado = Chamado(
        titulo="Erro ao emitir NFC-e no PDV",
        contato_nome="Marina Souza",
        tipo="bug",
        prioridade="alta",
        descricao="Ao emitir, o sistema fecha.",
    )
    caminho = tmp_path / "chamado.json"
    salvar_chamado_json(chamado, caminho)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert dados["titulo"] == "Erro ao emitir NFC-e no PDV"

    carregado = carregar_chamado_json(caminho)
    assert carregado == chamado


def test_salvar_e_carregar_txt_do_resumo(tmp_path):
    chamado = Chamado(titulo="Erro de login", contato_nome="Carlos Mendes", tipo="bug")
    caminho = tmp_path / "resumo.txt"
    salvar_chamado_txt(chamado, caminho)
    texto = caminho.read_text(encoding="utf-8")
    assert "Erro de login" in texto
    assert carregar_chamado_txt(caminho).titulo == "Erro de login"


def test_carregar_txt_preserva_descricao_e_contexto_tecnico():
    texto = """Título: Erro ao emitir NFC-e no PDV
Tipo: bug
Prioridade: alta
Status: aberto
Contato: Marina Souza
Empresa: Loja Exemplo
CNPJ: 11.222.333/0001-81
Telefone: (11) 91234-5678
E-mail: marina@exemplo.com
Descrição:
Ao clicar em emitir, o sistema trava.
Detalhes do contexto:
- Módulo/tela: Faturamento
- Versão: 4.8.1
- Quando começou: ontem
- Mudança recente: atualização do ERP
- Abrangência: loja inteira
Passos para reprodução:
1. Abre o PDV
2. Clica em emitir
Evidências:
- print_001.png
Reproduzido na base de teste: sim
"""
    chamado = carregar_chamado_txt(texto)
    assert chamado.descricao == "Ao clicar em emitir, o sistema trava."
    assert chamado.modulo == "Faturamento"
    assert chamado.versao == "4.8.1"
    assert chamado.passos_reproducao == ["Abre o PDV", "Clica em emitir"]
    assert chamado.evidencias == ["print_001.png"]
    assert chamado.reproduzido_base_teste is True


def test_demo_cenarios_tem_3_cenarios_validos():
    assert set(DEMO_CENARIOS) == {"impressora", "login", "banco"}
    for nome in DEMO_CENARIOS:
        chamado = carregar_demo(nome)
        assert isinstance(chamado, Chamado)
        assert chamado.contato_nome or chamado.titulo or chamado.descricao


def test_histórico_filtra_por_severidade_e_busca():
    historico = [
        {"titulo": "Erro de login", "status": "aberto", "severidade": "alta", "resumo": "falha no acesso ao portal"},
        {"titulo": "Impressora não printa", "status": "resolvido", "severidade": "media", "resumo": "problema de impressão"},
        {"titulo": "Banco lento", "status": "aberto", "severidade": "baixa", "resumo": "lentidão em consulta"},
    ]
    filtrado = filtrar_historico(historico, severidade="alta", busca="login")
    assert len(filtrado) == 1
    assert filtrado[0]["titulo"] == "Erro de login"

    filtrado_status = filtrar_historico(historico, status="aberto")
    assert {item["titulo"] for item in filtrado_status} == {"Erro de login", "Banco lento"}


def test_resumo_demo_narrativa_e_snapshot_do_chamado():
    narrativa = resumo_demo_narrativa("impressora")
    assert "impressão" in narrativa.lower() or "impressora" in narrativa.lower()

    chamado = Chamado(titulo="Erro de login", tipo="bug", prioridade="alta", descricao="Usuário não consegue acessar")
    snapshot = historico_a_partir_de_chamado(chamado)
    assert snapshot[0]["titulo"] == "Erro de login"
    assert snapshot[0]["severidade"] in {"alta", "media", "baixa"}


def test_gerar_chamado_final_painel_inclui_titulo_descricao_passos_e_solucao():
    chamado = Chamado(
        titulo="Erro ao emitir NFC-e no PDV",
        tipo="bug",
        descricao="Ao clicar em emitir, o sistema trava.",
        passos_reproducao=["Abre o PDV", "Clica em emitir"],
        evidencias=["print_001.png"],
        solucao="Reinstalei a biblioteca de NFC-e.",
    )
    texto = gerar_chamado_final_painel(chamado)
    assert "Título: Erro ao emitir NFC-e no PDV" in texto
    assert "Ao clicar em emitir, o sistema trava." in texto
    assert "Passos para reprodução" in texto
    assert "print_001.png" in texto
    assert "Solução aplicada" in texto


def test_assistente_orienta_analista_junior():
    chamado = Chamado(titulo="Falha de acesso", tipo="bug")
    orientacoes = sugestoes_do_assistente(chamado)
    assert orientacoes
    assert any("telefone" in item.lower() or "cliente" in item.lower() for item in orientacoes)


def test_guia_microfone_iniciante_e_abertura_windows(monkeypatch):
    passos = guia_microfone_iniciante()
    assert any("Configurações" in item or "Microfone" in item for item in passos)

    chamadas = []

    def fake_popen(comando, shell=False):
        chamadas.append((comando, shell))
        return object()

    monkeypatch.setattr("copiloto_n1.painel.platform.system", lambda: "Windows")
    monkeypatch.setattr("copiloto_n1.painel.subprocess.Popen", fake_popen)

    mensagem = abrir_configuracoes_microfone()
    assert "microfone" in mensagem.lower()
    assert chamadas
    assert "privacy-microphone" in chamadas[0][0]
