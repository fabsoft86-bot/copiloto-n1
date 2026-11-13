"""Painel Streamlit para revisão do chamado em tempo real."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, IO

import streamlit as st
from streamlit.components.v1 import html as st_html

from copiloto_n1.adaptadores import criar_adaptador
from copiloto_n1.extrator import ExtratorRegras
from copiloto_n1.perfil import carregar_perfil
from copiloto_n1.schemas import Chamado
from copiloto_n1.validador import validar

__all__ = [
    "classificar_severidade_por_nota",
    "renderizar_badge",
    "resumo_texto_limpo",
    "carregar_chamado_json",
    "salvar_chamado_json",
    "carregar_chamado_txt",
    "salvar_chamado_txt",
    "carregar_json",
    "salvar_json",
    "DEMO_CENARIOS",
    "carregar_demo",
    "resumo_demo_narrativa",
    "filtrar_historico",
    "registrar_historico",
    "sugestoes_do_assistente",
    "guia_microfone_iniciante",
    "abrir_configuracoes_microfone",
    "_montar_painel",
]


def classificar_severidade_por_nota(nota: int | float) -> str:
    """Classifica a qualidade do chamado por severidade visual."""
    valor = int(round(float(nota)))
    if valor < 40:
        return "alta"
    if valor < 80:
        return "media"
    return "baixa"


def badge_por_nota(nota: int | float) -> str:
    return classificar_severidade_por_nota(nota)


def _cor_badge(severidade: str) -> str:
    mapa = {
        "alta": "#fca5a5",
        "media": "#facc15",
        "baixa": "#86efac",
        "bloqueante": "#fca5a5",
        "importante": "#facc15",
        "sugestao": "#86efac",
    }
    return mapa.get(severidade.lower(), "#e5e7eb")


def renderizar_badge(severidade: str, texto: str | None = None) -> None:
    etiqueta = (texto or severidade).strip() or "sem status"
    cor = _cor_badge(severidade)
    st.markdown(
        f"<span style='display:inline-block; padding:0.25rem 0.75rem; border-radius:9999px; "
        f"background:{cor}; color:#111827; font-weight:600; font-size:0.8rem;'>{etiqueta}</span>",
        unsafe_allow_html=True,
    )


def resumo_texto_limpo(chamado: Chamado) -> str:
    """Gera uma versão limpa do resumo para exibição e cópia."""
    texto = chamado.gerar_chamado_final()
    linhas = [linha.strip() for linha in texto.splitlines()]
    return "\n".join(linha for linha in linhas if linha.strip())


def gerar_resumo_limpo(chamado: Chamado) -> str:
    return resumo_texto_limpo(chamado)


def gerar_chamado_final_painel(chamado: Chamado) -> str:
    """Gera o texto final do chamado em formato de revisão para N2/N3."""
    texto = chamado.gerar_chamado_final()
    return texto.strip()


def guia_microfone_iniciante() -> list[str]:
    """Lista passos simples para habilitar o microfone em linguagem de iniciante."""
    return [
        "1. Abra o menu Iniciar e clique em Configurações.",
        "2. Vá em Privacidade e segurança > Microfone.",
        "3. Ative a opção 'Acesso ao microfone'.",
        "4. Ative também 'Permitir que os apps usem o microfone'.",
        "5. Se o problema for no navegador, abra o site, clique no cadeado e permita o microfone.",
        "6. Recarregue a página e teste de novo.",
    ]


def _tentar_abrir_configuracao_microfone_no_navegador() -> None:
    """Tenta abrir a página do microfone no navegador/Windows quando possível."""
    st_html(
        """
        <script>
        try {
            const userAgent = navigator.userAgent || "";
            const windows = userAgent.includes('Windows');
            if (windows && typeof window !== 'undefined') {
                const target = 'ms-settings:privacy-microphone';
                window.location.href = target;
            }
        } catch (error) {
            console.log('microphone settings fallback', error);
        }
        </script>
        """,
        height=0,
    )


def abrir_configuracoes_microfone() -> str:
    """Abre diretamente a tela correta do Windows para ativar o microfone."""
    sistema = platform.system().lower()
    if sistema == "windows":
        comando = "start ms-settings:privacy-microphone"
        try:
            subprocess.Popen(comando, shell=True)
            _tentar_abrir_configuracao_microfone_no_navegador()
            return (
                "Abri a página correta do Windows para o microfone. "
                "Siga os passos abaixo:\n- " + "\n- ".join(guia_microfone_iniciante())
            )
        except OSError:
            _tentar_abrir_configuracao_microfone_no_navegador()
            return "Não foi possível abrir automaticamente. Vá em Configurações > Privacidade e segurança > Microfone e siga os passos abaixo:\n- " + "\n- ".join(guia_microfone_iniciante())

    _tentar_abrir_configuracao_microfone_no_navegador()
    return "No seu sistema, siga estas etapas:\n- " + "\n- ".join(guia_microfone_iniciante())


def carregar_chamado_json(origem: str | Path | IO[str] | IO[bytes]) -> Chamado:
    """Carrega um chamado a partir de texto JSON bruto ou de um caminho."""
    if hasattr(origem, "read"):
        conteudo = origem.read()
        if isinstance(conteudo, bytes):
            conteudo = conteudo.decode("utf-8")
    elif isinstance(origem, str):
        caminho = Path(origem)
        if caminho.exists():
            conteudo = caminho.read_text(encoding="utf-8")
        else:
            conteudo = origem
    else:
        conteudo = Path(origem).read_text(encoding="utf-8")
    return Chamado.model_validate(json.loads(conteudo))


def salvar_chamado_json(chamado: Chamado, destino: str | Path | None = None) -> str:
    """Serializa o chamado em JSON e o salva em disco, quando um destino for informado."""
    payload = chamado.model_dump(mode="json")
    texto = json.dumps(payload, ensure_ascii=False, indent=2)
    if destino is None:
        return texto
    caminho = Path(destino)
    if caminho.suffix.lower() != ".json":
        caminho = caminho.with_suffix(".json")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return str(caminho)


def _parsear_txt_para_chamado(conteudo: str) -> Chamado:
    """Tenta importar um resumo exportado em texto, ou cai para extração da conversa."""
    campos = {
        "titulo": "Título:",
        "tipo": "Tipo:",
        "prioridade": "Prioridade:",
        "status": "Status:",
        "contato_nome": "Contato:",
        "empresa": "Empresa:",
        "cnpj": "CNPJ:",
        "telefone": "Telefone:",
        "email": "E-mail:",
        "modulo": "Módulo/tela:",
        "versao": "Versão:",
        "quando_comecou": "Quando começou:",
        "mudanca_recente": "Mudança recente:",
        "escopo": "Abrangência:",
        "dependencias_externas": "Dependências externas:",
        "causa_raiz": "Causa raiz:",
        "solucao": "Solução aplicada:",
        "destino_escalonamento": "Destino do escalonamento:",
    }
    dados: dict[str, object] = {}
    linhas = conteudo.splitlines()
    stop_prefixes = (
        "Título:",
        "Tipo:",
        "Prioridade:",
        "Status:",
        "Contato:",
        "Empresa:",
        "CNPJ:",
        "Telefone:",
        "E-mail:",
        "Descrição:",
        "Detalhes do contexto:",
        "Passos para reprodução:",
        "Evidências:",
        "Reproduzido na base de teste:",
        "Causa raiz:",
        "Solução aplicada:",
        "Destino do escalonamento:",
        "Módulo/tela:",
        "Versão:",
        "Quando começou:",
        "Mudança recente:",
        "Abrangência:",
        "Dependências externas:",
        "- Módulo/tela:",
        "- Versão:",
        "- Quando começou:",
        "- Mudança recente:",
        "- Abrangência:",
        "- Dependências externas:",
    )

    def _valor_aceitavel(valor: str | None) -> bool:
        if valor is None:
            return False
        return bool(valor.strip()) and valor.strip().lower() not in {
            "não informado",
            "não informada",
            "nao informado",
            "nao informada",
        }

    def _ler_blocos(inicio: int, interromper: tuple[str, ...]) -> tuple[list[str], int]:
        itens: list[str] = []
        i = inicio
        while i < len(linhas):
            texto = linhas[i].strip()
            if not texto:
                i += 1
                continue
            if any(texto.startswith(prefixo) for prefixo in interromper):
                break
            if texto.startswith("- "):
                itens.append(texto[2:].strip())
            elif re.match(r"^\d+\.\s*", texto):
                itens.append(re.sub(r"^\d+\.\s*", "", texto))
            else:
                itens.append(texto)
            i += 1
        return itens, i

    i = 0
    while i < len(linhas):
        linha = linhas[i].strip()
        if not linha:
            i += 1
            continue

        for campo, prefixo in campos.items():
            if linha.startswith(prefixo):
                valor = linha[len(prefixo) :].strip()
                if _valor_aceitavel(valor):
                    dados[campo] = valor
                i += 1
                break
        else:
            if linha.startswith("- Módulo/tela:"):
                valor = linha.split(":", 1)[1].strip()
                if _valor_aceitavel(valor):
                    dados["modulo"] = valor
                i += 1
                continue
            if linha.startswith("- Versão:"):
                valor = linha.split(":", 1)[1].strip()
                if _valor_aceitavel(valor):
                    dados["versao"] = valor
                i += 1
                continue
            if linha.startswith("- Quando começou:"):
                valor = linha.split(":", 1)[1].strip()
                if _valor_aceitavel(valor):
                    dados["quando_comecou"] = valor
                i += 1
                continue
            if linha.startswith("- Mudança recente:"):
                valor = linha.split(":", 1)[1].strip()
                if _valor_aceitavel(valor):
                    dados["mudanca_recente"] = valor
                i += 1
                continue
            if linha.startswith("- Abrangência:"):
                valor = linha.split(":", 1)[1].strip()
                if _valor_aceitavel(valor):
                    dados["escopo"] = valor
                i += 1
                continue
            if linha.startswith("- Dependências externas:"):
                valor = linha.split(":", 1)[1].strip()
                if _valor_aceitavel(valor):
                    dados["dependencias_externas"] = valor
                i += 1
                continue
            if linha.startswith("Descrição:"):
                valor = linha[len("Descrição:") :].strip()
                bloco = [valor] if _valor_aceitavel(valor) else []
                if not bloco:
                    bloco = []
                j = i + 1
                while j < len(linhas):
                    proximo = linhas[j].strip()
                    if not proximo:
                        j += 1
                        continue
                    if any(proximo.startswith(prefixo) for prefixo in stop_prefixes):
                        break
                    if proximo.startswith("- "):
                        bloco.append(proximo[2:].strip())
                    elif re.match(r"^\d+\.\s*", proximo):
                        bloco.append(re.sub(r"^\d+\.\s*", "", proximo))
                    else:
                        bloco.append(proximo)
                    j += 1
                dados["descricao"] = "\n".join(item for item in bloco if item).strip()
                i = j
                continue
            if linha.startswith("Passos para reprodução:"):
                itens, i = _ler_blocos(i + 1, ("Evidências:", "Reproduzido na base de teste:", "Causa raiz:", "Solução aplicada:", "Destino do escalonamento:"))
                dados["passos_reproducao"] = [item for item in itens if item]
                continue
            if linha.startswith("Evidências:"):
                itens, i = _ler_blocos(i + 1, ("Reproduzido na base de teste:", "Causa raiz:", "Solução aplicada:", "Destino do escalonamento:"))
                dados["evidencias"] = [item for item in itens if item]
                continue
            if linha.startswith("Reproduzido na base de teste:"):
                valor = linha.split(":", 1)[1].strip().lower()
                dados["reproduzido_base_teste"] = valor in {"sim", "true", "s", "yes"}
                i += 1
                continue
            if linha.startswith("Causa raiz:"):
                valor = linha[len("Causa raiz:") :].strip()
                if _valor_aceitavel(valor):
                    dados["causa_raiz"] = valor
                i += 1
                continue
            if linha.startswith("Solução aplicada:"):
                valor = linha[len("Solução aplicada:") :].strip()
                if _valor_aceitavel(valor):
                    dados["solucao"] = valor
                i += 1
                continue
            if linha.startswith("Destino do escalonamento:"):
                valor = linha[len("Destino do escalonamento:") :].strip()
                if _valor_aceitavel(valor):
                    dados["destino_escalonamento"] = valor
                i += 1
                continue
            i += 1

    if dados:
        return Chamado(**dados)
    return ExtratorRegras().extrair(conteudo)


def carregar_chamado_txt(origem: str | Path | IO[str] | IO[bytes]) -> Chamado:
    """Carrega texto de conversa ou de um resumo exportado em TXT."""
    if hasattr(origem, "read"):
        conteudo = origem.read()
        if isinstance(conteudo, bytes):
            conteudo = conteudo.decode("utf-8")
    elif isinstance(origem, str):
        caminho = Path(origem)
        if caminho.exists():
            conteudo = caminho.read_text(encoding="utf-8")
        else:
            conteudo = origem
    else:
        conteudo = Path(origem).read_text(encoding="utf-8")
    return _parsear_txt_para_chamado(conteudo)


def salvar_chamado_txt(chamado: Chamado, destino: str | Path | None = None) -> str:
    """Salva o resumo texto do chamado em TXT."""
    texto = resumo_texto_limpo(chamado)
    if destino is None:
        return texto
    caminho = Path(destino)
    if caminho.suffix.lower() != ".txt":
        caminho = caminho.with_suffix(".txt")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return str(caminho)


carregar_json = carregar_chamado_json
salvar_json = salvar_chamado_json

DEMO_NARRATIVAS: dict[str, str] = {
    "impressora": "O cliente reporta falha na impressão de NFC-e após atualização do ERP. O analista precisa confirmar a reprodução, validar o módulo e registrar urgência operacional.",
    "login": "Usuários do setor de RH não conseguem acessar o portal após a troca de senha vigente. O foco é validar a origem do problema e confirmar se há impacto coletivo.",
    "banco": "A aplicação está com lentidão e indisponibilidade intermitente no banco. A equipe precisa validar a gravidade, a recorrência e possíveis dependências de infraestrutura.",
}


def resumo_demo_narrativa(nome: str) -> str:
    """Retorna a narrativa breve da demo para apresentação."""
    return DEMO_NARRATIVAS.get(nome, "Cenário demonstrativo do Copiloto N1.")


def filtrar_historico(
    historico: list[dict[str, str]],
    severidade: str | None = None,
    status: str | None = None,
    busca: str = "",
) -> list[dict[str, str]]:
    """Filtra itens do histórico por severidade, status e texto livre."""
    termo = busca.strip().lower()
    itens = list(historico)
    if severidade and severidade != "todas":
        itens = [item for item in itens if (item.get("severidade") or "").lower() == severidade.lower()]
    if status and status != "todos":
        itens = [item for item in itens if (item.get("status") or "").lower() == status.lower()]
    if termo:
        itens = [
            item
            for item in itens
            if termo in (item.get("titulo") or "").lower()
            or termo in (item.get("resumo") or "").lower()
            or termo in (item.get("tipo") or "").lower()
        ]
    return itens


def historico_a_partir_de_chamado(chamado: Chamado, limite: int = 8) -> list[dict[str, str]]:
    """Gera um snapshot do chamado para manter um histórico recente do painel."""
    perfil = carregar_perfil("software_house")
    validacao = validar(chamado, perfil)
    item = {
        "titulo": chamado.titulo or "Chamado sem título",
        "tipo": chamado.tipo or "sem tipo",
        "prioridade": chamado.prioridade or "media",
        "status": chamado.status or "aberto",
        "severidade": classificar_severidade_por_nota(validacao.nota),
        "resumo": resumo_texto_limpo(chamado),
        "quando": datetime.now().strftime("%d/%m %H:%M"),
    }
    historico = [item]
    return historico[:limite]


def registrar_historico(chamado: Chamado, limite: int = 8) -> list[dict[str, str]]:
    """Adiciona um chamado ao histórico de sessão do usuário."""
    historico = list(st.session_state.get("historico_chamados", []))
    item = historico_a_partir_de_chamado(chamado, limite=limite)[0]
    if not any(
        (entry.get("titulo"), entry.get("quando"), entry.get("status"))
        == (item["titulo"], item["quando"], item["status"])
        for entry in historico
    ):
        historico.insert(0, item)
    historico = historico[:limite]
    st.session_state["historico_chamados"] = historico
    return historico


def sugestoes_do_assistente(chamado: Chamado) -> list[str]:
    """Cria um conjunto de sugestões executáveis para analistas juniores."""
    perfil = carregar_perfil("software_house")
    validacao = validar(chamado, perfil)
    sugestoes: list[str] = []
    if not chamado.titulo:
        sugestoes.append("Crie um título objetivo em 5 a 12 palavras, com o problema principal e o impacto.")
    if not chamado.contato_nome:
        sugestoes.append("Confirme o nome do cliente antes de fechar o registro.")
    if not chamado.telefone or chamado.telefone_confirmado is not True:
        sugestoes.append("Peça e confirme o telefone com o cliente para evitar retrabalho no próximo nível.")
    if not chamado.descricao:
        sugestoes.append("Registre em uma frase clara o problema, impacto e quando começou.")
    if not chamado.passos_reproducao:
        sugestoes.append("Tente reproduzir o problema e anote passos simples em ordem.")
    if not chamado.evidencias:
        sugestoes.append("Solicite print, log, erro ou evidência antes de escalar.")
    if not sugestoes and not validacao.pendencias:
        sugestoes.append("Registro completo. Revise o resumo, confirme prioridade e exporte para o próximo nível.")
    if not sugestoes:
        for pendencia in validacao.pendencias[:3]:
            sugestoes.append(f"Pergunte: {pendencia.pergunta}")
    return sugestoes


DEMO_CENARIOS: dict[str, str] = {
    "impressora": """Analista: bom dia, preciso abrir um chamado.\nCliente: boa tarde. A impressora fiscal não imprime desde a manhã.\nCliente: ela está piscando em amarelo e os documentos não saem.\nCliente: meu nome é Marina Souza, meu e-mail é marina.souza@exemplo.com.br, telefone (11) 91234-5678, CNPJ 11.222.333/0001-81.\nCliente: atualizei o sistema ontem e a impressora não responde mais.\nCliente: a falha acontece quando tento emitir uma nota fiscal.\nCliente: reproduz no PDV e no caixa da loja, sempre na emissão de NFC-e.\nCliente: a impressora pertence ao módulo de faturamento, versao 4.8.1.\nCliente: o problema começou ontem após a atualização do ERP.\nCliente: precisamos do suporte urgente.\nCliente: não foi feita nenhuma mudança de hardware.\nAnalista: obrigada, vou registrar o problema.""",
    "login": """Analista: bom dia, vamos abrir um chamado.\nCliente: meu nome é Carlos Mendes.\nCliente: eu não consigo entrar no portal da empresa depois da mudança de senha.\nCliente: meu email é carlos.mendes@empresa.com.br\nCliente: o sistema retorna erro de login mesmo com a senha correta.\nCliente: uso o módulo de RH, versão 3.2.0.\nCliente: acontece ao abrir a tela de login e digitar o usuário e senha.\nCliente: a falha começou depois da atualização de acesso.\nCliente: o problema é recorrente para todos os usuários do setor.\nCliente: eu quero saber se o problema é do meu usuário ou do sistema.\nAnalista: entendi, vou registrar.""",
    "banco": """Analista: qual o problema?\nCliente: meu nome é Juliana Costa, telefone (21) 99887-4433.\nCliente: o banco de dados da aplicação está lento e cai de vez em quando.\nCliente: o erro ocorre no ERP, módulo financeiro, versão 5.1.4.\nCliente: o sistema fecha conexões sem motivo e a operação para.\nCliente: o problema começou nesta semana e é recorrente durante a noite.\nCliente: temos dependência do SQL Server e do provedor de rede.\nCliente: não consigo dizer a causa raiz ainda.\nCliente: preciso de ajuda para diagnosticar e recuperar o serviço.\nAnalista: obrigado.""",
}


def carregar_demo(nome: str) -> Chamado:
    """Carrega um cenário demo pré-definido para apresentação."""
    if nome not in DEMO_CENARIOS:
        raise ValueError(f"Cenário demo não encontrado: {nome!r}")
    return ExtratorRegras().extrair(DEMO_CENARIOS[nome])


def _normalizar_texto(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "sim" if valor else "nao"
    if isinstance(valor, list):
        return "\n".join(str(item) for item in valor)
    return str(valor)


def _parse_lista(valor: str) -> list[str]:
    return [linha.strip() for linha in valor.splitlines() if linha.strip()]


def _parse_bool(valor: str) -> bool | None:
    texto = valor.strip().lower()
    if texto in {"", "nao", "não", "false", "false"}:
        return False if texto else None
    if texto in {"sim", "true"}:
        return True
    return None


def _campos_do_formulario(chamado: Chamado) -> dict[str, object]:
    return {
        "contato_nome": _normalizar_texto(chamado.contato_nome),
        "empresa": _normalizar_texto(chamado.empresa),
        "cnpj": _normalizar_texto(chamado.cnpj),
        "telefone": _normalizar_texto(chamado.telefone),
        "telefone_confirmado": bool(chamado.telefone_confirmado) if chamado.telefone_confirmado is not None else False,
        "email": _normalizar_texto(chamado.email),
        "titulo": _normalizar_texto(chamado.titulo),
        "tipo": _normalizar_texto(chamado.tipo),
        "prioridade": _normalizar_texto(chamado.prioridade),
        "status": _normalizar_texto(chamado.status),
        "modulo": _normalizar_texto(chamado.modulo),
        "versao": _normalizar_texto(chamado.versao),
        "descricao": _normalizar_texto(chamado.descricao),
        "quando_comecou": _normalizar_texto(chamado.quando_comecou),
        "recorrente": bool(chamado.recorrente) if chamado.recorrente is not None else False,
        "mudanca_recente": _normalizar_texto(chamado.mudanca_recente),
        "escopo": _normalizar_texto(chamado.escopo),
        "dependencias_externas": _normalizar_texto(chamado.dependencias_externas),
        "passos_reproducao": "\n".join(chamado.passos_reproducao),
        "evidencias": "\n".join(chamado.evidencias),
        "reproduzido_base_teste": bool(chamado.reproduzido_base_teste) if chamado.reproduzido_base_teste is not None else False,
        "causa_raiz": _normalizar_texto(chamado.causa_raiz),
        "solucao": _normalizar_texto(chamado.solucao),
        "destino_escalonamento": _normalizar_texto(chamado.destino_escalonamento),
        "retorno_ao_cliente_feito": bool(chamado.retorno_ao_cliente_feito) if chamado.retorno_ao_cliente_feito is not None else False,
    }


def _atualizar_chamado(chamado: Chamado, formulario: dict[str, object]) -> Chamado:
    dados = chamado.model_dump()
    for campo, valor in formulario.items():
        if campo in {"telefone_confirmado", "recorrente", "reproduzido_base_teste", "retorno_ao_cliente_feito"}:
            dados[campo] = bool(valor)
            continue
        if campo in {"passos_reproducao", "evidencias"}:
            dados[campo] = _parse_lista(str(valor))
            continue
        if campo in {"tipo", "prioridade", "status"} and str(valor).strip() == "":
            dados[campo] = None
            continue
        if campo in {"tipo", "prioridade", "status"}:
            dados[campo] = str(valor).strip() or None
            continue
        dados[campo] = str(valor).strip() or None
    return Chamado(**dados)


def _carregar_painel(chamada: str | None = None, chamado_inicial: Chamado | None = None) -> Chamado:
    perfil = carregar_perfil("software_house")
    if chamada and chamada.strip():
        base = ExtratorRegras().extrair(chamada, chamado_inicial)
    else:
        base = chamado_inicial or Chamado()
    res = validar(base, perfil)
    st.session_state["perfil"] = perfil
    st.session_state["validacao"] = res
    return base


def _resumo_rapido(chamado: Chamado) -> str:
    """Cria um texto curto para orientar o analista na tela principal."""
    titulo = chamado.titulo or "Chamado sem título"
    tipo = chamado.tipo or "tipo não informado"
    status = chamado.status or "aberto"
    return f"{titulo} · {tipo} · {status}"


def _copiar_texto_para_area_transferencia(texto: str, mensagem: str) -> None:
    st_html(
        f"""
        <script>
        navigator.clipboard.writeText({json.dumps(texto)}).catch(() => {{}});
        </script>
        """,
        height=0,
    )
    st.toast(mensagem)


def _copiar_resumo_para_area_transferencia(chamado: Chamado) -> None:
    _copiar_texto_para_area_transferencia(resumo_texto_limpo(chamado), "Resumo copiado para a área de transferência.")


def _copiar_pergunta_sugerida(resultado: Any) -> None:
    pergunta = resultado.pendencias[0].pergunta if getattr(resultado, "pendencias", None) else "Nenhuma pendência ativa no momento."
    _copiar_texto_para_area_transferencia(pergunta, "Pergunta sugerida copiada para a área de transferência.")


def _configuracao_backend(backend: str) -> dict[str, object]:
    """Monta a configuração do backend atual e valida campos obrigatórios."""
    config = {
        "url": st.session_state.get("backend_url", ""),
        "app_token": st.session_state.get("glpi_app_token", ""),
        "user_token": st.session_state.get("glpi_user_token", ""),
        "api_token": st.session_state.get("glpi_api_token", "") or st.session_state.get("glpi_session_token", ""),
        "session_token": st.session_state.get("glpi_session_token", "") or st.session_state.get("glpi_api_token", ""),
        "entity_id": st.session_state.get("glpi_entity_id", 0),
        "user": st.session_state.get("jira_user", ""),
        "token": st.session_state.get("jira_token", ""),
        "password": st.session_state.get("jira_password", ""),
        "project_key": st.session_state.get("jira_project_key", "SUP"),
        "issue_type": st.session_state.get("jira_issue_type", "Task"),
    }

    if backend == "glpi":
        campos_faltando = []
        if not str(config.get("url", "")).strip():
            campos_faltando.append("URL do GLPI")
        if not str(config.get("app_token", "")).strip():
            campos_faltando.append("App token")
        if not str(config.get("user_token", "")).strip():
            campos_faltando.append("User token")
        if campos_faltando:
            raise ValueError("Configuração incompleta para GLPI: " + ", ".join(campos_faltando) + ".")

    if backend == "jira":
        campos_faltando = []
        if not str(config.get("url", "")).strip():
            campos_faltando.append("URL do Jira")
        if not str(config.get("user", "")).strip():
            campos_faltando.append("Usuário Jira")
        token = str(config.get("token", "") or config.get("password", "") or "").strip()
        if not token:
            campos_faltando.append("Token ou senha Jira")
        if campos_faltando:
            raise ValueError("Configuração incompleta para Jira: " + ", ".join(campos_faltando) + ".")

    return config


def _payload_backend(chamado: Chamado, backend: str) -> dict[str, object]:
    """Cria uma representação JSON do payload que será enviado ao backend."""
    if backend == "glpi":
        nome = chamado.titulo or "Chamado sem título"
        if chamado.modulo:
            nome = f"[{chamado.modulo}] {nome}"
        return {
            "input": {
                "name": nome,
                "content": chamado.gerar_chamado_final(),
                "status": 1,
                "urgency": 4 if (chamado.prioridade or "media") == "alta" else 3 if (chamado.prioridade or "media") == "media" else 2,
                "priority": 1 if (chamado.prioridade or "media") == "alta" else 2 if (chamado.prioridade or "media") == "media" else 3,
                "type": 1,
                "entities_id": int(st.session_state.get("glpi_entity_id", 0) or 0),
            }
        }

    if backend == "jira":
        summary = chamado.titulo or "Chamado sem título"
        if chamado.modulo:
            summary = f"[{chamado.modulo}] {summary}"
        return {
            "fields": {
                "project": {"key": st.session_state.get("jira_project_key", "SUP")},
                "summary": summary,
                "description": chamado.gerar_chamado_final(),
                "issuetype": {"name": st.session_state.get("jira_issue_type", "Task")},
                "priority": {"name": {"baixa": "Low", "media": "Medium", "alta": "High"}.get((chamado.prioridade or "media").lower(), "Medium")},
                "labels": ["n1", "suporte", "copiloto"],
            }
        }

    return {}


def _validar_conexao_backend(backend: str) -> bool:
    if backend == "arquivo":
        return True
    config = _configuracao_backend(backend)
    adaptador = criar_adaptador(backend, **config)
    return adaptador.validar_conexao()


def _enviar_para_backend(chamado: Chamado) -> str:
    backend = st.session_state.get("backend_export", "arquivo")
    if backend == "arquivo":
        return "arquivo"

    config = _configuracao_backend(backend)
    adaptador = criar_adaptador(backend, **config)
    if hasattr(adaptador, "validar_conexao"):
        adaptador.validar_conexao()
    identificador = str(adaptador.criar_chamado(chamado))
    st.session_state["ultimo_envio_backend"] = {
        "backend": backend,
        "identificador": identificador,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return identificador


def _montar_painel() -> None:
    st.set_page_config(page_title="N1 Flow", page_icon="⚡")
    st.markdown(
        """
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
        <meta name="theme-color" content="#2563eb">
        <link rel="manifest" href="manifest.webmanifest">
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%); }
        .block-container { padding-top: 1.25rem; }
        div[data-testid="stSidebar"] { background: rgba(15, 23, 42, 0.96); }
        div[data-testid="stMetricValue"] { font-size: 1.5rem; }
        .card { background: rgba(255,255,255,0.97); border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem; box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06); }
        .step-pill { display:inline-block; background:linear-gradient(135deg, #dbeafe 0%, #ede9fe 100%); color:#0f172a; border: 1px solid #bfdbfe; border-radius:999px; padding:.38rem .8rem; font-weight:700; margin-right:.5rem; }
        .quick-card { background: linear-gradient(135deg, #eff6ff 0%, #faf5ff 100%); border: 1px solid #dbeafe; border-radius: 16px; padding: 0.9rem 1rem; margin: 0.8rem 0 1rem 0; }
        .status-pill { display:inline-block; padding:0.35rem 0.75rem; border-radius:999px; font-size:0.78rem; font-weight:700; }
        .card-section { background: rgba(255,255,255,0.94); border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 8px 20px rgba(15,23,42,0.04); }
        .status-card { border-radius: 16px; padding: 0.9rem 1rem; border: 1px solid rgba(15,23,42,0.08); border-left: 6px solid rgba(15,23,42,0.2); box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08); min-height: 110px; background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,250,252,0.94)); }
        .status-label { font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.8; font-weight: 700; }
        .status-value { font-size: 1.8rem; font-weight: 800; line-height: 1.2; margin-top: 0.5rem; }
        .section-tag { display:inline-block; background: linear-gradient(135deg, #eff6ff 0%, #ede9fe 100%); border: 1px solid #c7d2fe; color: #111827; border-radius: 999px; padding: 0.3rem 0.8rem; font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 700; margin-bottom: 0.75rem; }
        .section-shell { background: rgba(255,255,255,0.78); border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 10px 24px rgba(15,23,42,0.04); }
        .pendencia-card { background: #fff; border-left: 6px solid var(--cor-severidade, #64748b); border-radius: 12px; padding: 0.8rem 0.9rem; margin-bottom: 0.8rem; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04); }
        .pendencia-severidade { display:inline-block; color:#111827; font-size:0.72rem; font-weight:700; padding:0.25rem 0.6rem; border-radius:999px; margin-bottom:0.5rem; }
        .foco-minimal { max-width: 1000px; margin: 0 auto; }
        .fixed-layout { max-width: 1600px; }
        .microphone-help { background: linear-gradient(135deg, #dbeafe 0%, #ede9fe 100%); border: 2px solid #818cf8; border-radius: 18px; padding: 1rem; margin-top: 0.5rem; box-shadow: 0 10px 22px rgba(99, 102, 241, 0.15); }
        .microphone-help h4 { margin: 0 0 0.7rem 0; color: #111827; }
        .microphone-help ol { margin: 0; padding-left: 1.1rem; color: #1f2937; }
        .microphone-help li { margin-bottom: 0.35rem; }
        .microphone-cta { background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: white; border: none; border-radius: 12px; padding: 0.8rem 1.2rem; font-weight: 700; }
        .quick-action { border-radius: 12px; font-weight: 600; }
        .stButton > button,
        div[data-testid="stDownloadButton"] > button,
        button[kind="primary"],
        button[kind="secondary"] {
            background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            min-height: 46px !important;
            padding: 0.7rem 1.1rem !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
            transition: transform 0.15s ease, filter 0.15s ease, box-shadow 0.15s ease !important;
        }
        .stButton > button:hover,
        div[data-testid="stDownloadButton"] > button:hover,
        button[kind="primary"]:hover,
        button[kind="secondary"]:hover {
            filter: brightness(1.04) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 12px 24px rgba(37, 99, 235, 0.28) !important;
        }
        .stButton > button:focus,
        div[data-testid="stDownloadButton"] > button:focus,
        button[kind="primary"]:focus,
        button[kind="secondary"]:focus {
            outline: 3px solid rgba(96, 165, 250, 0.55) !important;
            outline-offset: 2px !important;
        }
        @media (max-width: 768px) {
            .block-container { padding-left: 0.75rem !important; padding-right: 0.75rem !important; }
            .card, .card-section, .section-shell { padding: 0.8rem !important; }
            .status-value { font-size: 1.35rem !important; }
            .status-card { min-height: auto; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("N1 Flow")
    st.caption("Assistente de suporte N1")

    st.markdown(
        """
        <script>
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function() {
                navigator.serviceWorker.register('sw.js').catch(function() {});
            });
        }
        </script>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='card'><span class='step-pill'>1. Registrar</span><span class='step-pill'>2. Validar</span><span class='step-pill'>3. Escalar</span></div>",
        unsafe_allow_html=True,
    )

    perfil = carregar_perfil("software_house")
    if "chamado" not in st.session_state:
        st.session_state.chamado = Chamado()
    if "conversa" not in st.session_state:
        st.session_state.conversa = ""
    if "historico_chamados" not in st.session_state:
        st.session_state.historico_chamados = []
    if "chamado_final" not in st.session_state:
        st.session_state.chamado_final = gerar_chamado_final_painel(st.session_state.chamado)
    if "modo_focado" not in st.session_state:
        st.session_state.modo_focado = False
    if "ultimo_envio_backend" not in st.session_state:
        st.session_state.ultimo_envio_backend = {}

    validacao_atual = validar(st.session_state.chamado, perfil)
    nota = validacao_atual.nota
    severidade_atual = classificar_severidade_por_nota(nota)

    with st.sidebar:
        st.markdown("## Atalhos")
        st.session_state.modo_focado = st.checkbox("Modo focado", value=st.session_state.modo_focado)

        st.markdown(
            """
            <div class='microphone-help'>
                <h4>🎙️ Microfone</h4>
                <p>Se precisar, abra a configuração do Windows.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ativar microfone", use_container_width=True, help="Abre as configurações do microfone do Windows"):
            st.info(abrir_configuracoes_microfone())
        with st.expander("Como ativar", expanded=False):
            st.markdown(
                """
                <ol>
                    <li>Abra <strong>Configurações</strong>.</li>
                    <li>Vá em <strong>Privacidade e segurança</strong>.</li>
                    <li>Clique em <strong>Microfone</strong>.</li>
                    <li>Ative <strong>Acesso ao microfone</strong>.</li>
                    <li>Permita o uso no navegador.</li>
                </ol>
                """,
                unsafe_allow_html=True,
            )

        if not st.session_state.modo_focado:
            filtro_severidade = st.selectbox("Severidade", options=["todas", "alta", "media", "baixa"], index=0)
            filtro_status = st.selectbox("Status", options=["todos", "aberto", "resolvido", "escalado"], index=0)
            busca_historico = st.text_input("Buscar no histórico", value="")

            historico_filtrado = filtrar_historico(
                st.session_state.get("historico_chamados", []),
                severidade=filtro_severidade,
                status=filtro_status,
                busca=busca_historico,
            )
            if historico_filtrado:
                for item in historico_filtrado:
                    if st.button(
                        f"{item.get('titulo', 'Sem título')} · {item.get('severidade', 'media')}",
                        key=f"hist_{item.get('titulo', 'sem_titulo')}_{item.get('quando', '')}",
                    ):
                        st.session_state.chamado = carregar_chamado_txt(item["resumo"]) if item.get("resumo") else st.session_state.chamado
                        st.session_state.conversa = item["resumo"]
                        st.session_state.chamado_final = gerar_chamado_final_painel(st.session_state.chamado)
                        st.rerun()
            else:
                st.info("Ainda não há histórico do atendimento.")

            st.markdown("### Demo")
            demo_nome = st.selectbox("Cenário", options=["impressora", "login", "banco"], index=0)
            st.write(resumo_demo_narrativa(demo_nome))
            if st.button("Carregar demo selecionada"):
                st.session_state.chamado = carregar_demo(demo_nome)
                st.session_state.conversa = DEMO_CENARIOS[demo_nome]
                st.session_state.chamado_final = gerar_chamado_final_painel(st.session_state.chamado)
                registrar_historico(st.session_state.chamado)
                st.rerun()

        st.markdown("---")
        if st.button("Limpar formulário"):
            st.session_state.chamado = Chamado()
            st.session_state.conversa = ""
            st.session_state.chamado_final = ""
            st.rerun()

    if st.session_state.modo_focado:
        st.markdown('<div class="foco-minimal">', unsafe_allow_html=True)
    st.markdown('<div class="fixed-layout">', unsafe_allow_html=True)

    cores_status = {
        "alta": "#fee2e2",
        "media": "#fef3c7",
        "baixa": "#dcfce7",
        "aberto": "#dbeafe",
        "resolvido": "#dcfce7",
        "escalado": "#fbcfe8",
        "bloqueante": "#fecaca",
        "importante": "#fef3c7",
        "sugestao": "#dcfce7",
    }

    def _card_status(label: str, valor: str, tonalidade: str) -> str:
        return (
            f"<div class='status-card' style='background:{cores_status.get(tonalidade.lower(), '#e2e8f0')};'>"
            f"<div class='status-label'>{label}</div><div class='status-value'>{valor}</div></div>"
        )

    col_nota, col_pendencias, col_status, col_prioridade = st.columns(4, gap="large")
    with col_nota:
        st.markdown(_card_status("Nota atual", f"{nota}/100", "media" if nota < 80 else "baixa"), unsafe_allow_html=True)
    with col_pendencias:
        tone = "bloqueante" if validacao_atual.pendencias else "sugestao"
        st.markdown(_card_status("Pendências", str(len(validacao_atual.pendencias)), tone), unsafe_allow_html=True)
    with col_status:
        estado = (st.session_state.chamado.status or "aberto").lower()
        st.markdown(_card_status("Status", st.session_state.chamado.status or "aberto", estado), unsafe_allow_html=True)
    with col_prioridade:
        st.markdown(_card_status("Severidade", severidade_atual, severidade_atual), unsafe_allow_html=True)

    st.markdown(
        f"<div class='quick-card'><strong>Resumo rápido:</strong> {_resumo_rapido(st.session_state.chamado)}</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.modo_focado:
        st.info("Modo focado ativo: revisão mínima, com atenção ao que falta para fechar o chamado.")

    col_entrada, col_formulario = st.columns([1.05, 1.95], gap="large")

    with col_entrada:
        st.markdown("<div class='section-shell'>", unsafe_allow_html=True)
        st.markdown("<div class='section-tag'>Registro do atendimento</div>", unsafe_allow_html=True)
        st.subheader("Atendimento em andamento")
        st.caption("Registre WhatsApp, chat, ligação ou texto digitado e deixe o assistente transformar isso em registro útil.")

        if not st.session_state.modo_focado:
            if st.button("🎤 Microfone"):
                st.components.v1.html(
                    """
                    <script>
                    (() => {
                        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                        if (!SpeechRecognition) {
                            alert('Seu navegador não suporta ditado por voz. Use Chrome ou Edge e permita o microfone no site.');
                            return;
                        }

                        const parentDocument = window.parent && window.parent.document ? window.parent.document : document;
                        const findTarget = () => {
                            const candidates = Array.from(parentDocument.querySelectorAll('textarea'));
                            return candidates.find((el) => {
                                const label = (el.getAttribute('aria-label') || '').toLowerCase();
                                const placeholder = (el.getAttribute('placeholder') || '').toLowerCase();
                                const value = (el.value || '').toLowerCase();
                                return /conversa|atendimento|histórico|mensagem|chat|texto/i.test(label + ' ' + placeholder + ' ' + value);
                            }) || candidates[0];
                        };

                        const target = findTarget();
                        if (!target) {
                            alert('Não encontrei o campo de texto da conversa. Tente clicar no campo de atendimento antes de ativar o microfone.');
                            return;
                        }

                        const recognition = new SpeechRecognition();
                        recognition.lang = 'pt-BR';
                        recognition.continuous = false;
                        recognition.interimResults = false;

                        recognition.onresult = (event) => {
                            const transcript = event.results[event.results.length - 1][0].transcript;
                            const atual = target.value || '';
                            target.value = (atual ? atual + '\n' : '') + transcript;
                            target.dispatchEvent(new Event('input', { bubbles: true }));
                            target.dispatchEvent(new Event('change', { bubbles: true }));
                            target.focus();
                        };

                        recognition.onerror = () => {
                            alert('Não consegui captar o áudio. Verifique se o navegador tem permissão para usar o microfone.');
                        };

                        try {
                            recognition.start();
                        } catch (error) {
                            alert('O microfone já está em uso. Feche outras abas e tente novamente.');
                        }
                    })();
                    </script>
                    """,
                    height=0,
                )

            uploads_evidencias = st.file_uploader(
                "📎 Prints / evidências da manutenção",
                type=["png", "jpg", "jpeg", "webp", "bmp", "pdf", "txt"],
                accept_multiple_files=True,
                key="evidencias_upload",
            )
            if uploads_evidencias:
                anexos = list(st.session_state.chamado.evidencias)
                for arquivo in uploads_evidencias:
                    marcador = f"[Print anexado] {arquivo.name} ({arquivo.type or 'arquivo'} / {arquivo.size} bytes)"
                    if marcador not in anexos:
                        anexos.append(marcador)
                st.session_state.chamado.evidencias = anexos
                st.session_state.chamado_final = gerar_chamado_final_painel(st.session_state.chamado)
                st.success(f"{len(uploads_evidencias)} evidência(s) anexada(s) ao chamado.")
            if st.session_state.chamado.evidencias:
                st.caption("Evidências anexadas:")
                for item in st.session_state.chamado.evidencias[-5:]:
                    st.write(f"- {item}")

            conversa = st.text_area(
                "Conversa / WhatsApp / histórico do atendimento",
                value=st.session_state.conversa,
                height=240,
                key="conversa_input",
            )
            if st.button("Extrair dados do atendimento") and conversa.strip():
                st.session_state.conversa = conversa
                st.session_state.chamado = ExtratorRegras().extrair(conversa, st.session_state.chamado)
                registrar_historico(st.session_state.chamado)

            st.subheader("Ações rápidas")
            st.caption("Ações principais do atendimento")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.download_button(
                    label="💾 Salvar JSON",
                    data=salvar_chamado_json(st.session_state.chamado),
                    file_name="chamado.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json",
                )
            with col_b:
                st.download_button(
                    label="📄 Salvar TXT",
                    data=salvar_chamado_txt(st.session_state.chamado),
                    file_name="chamado_resumo.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="download_txt",
                )
            with col_c:
                if st.button("📋 Copiar resumo", use_container_width=True, key="copiar_resumo_acao"):
                    _copiar_resumo_para_area_transferencia(st.session_state.chamado)

            st.caption("Dica: o analista decide o que salva; o copilot sugere e preenche os campos vazios.")

            with st.expander("Avançado: backend GLPI / Jira"):
                opcoes_backend = ["arquivo", "glpi", "jira"]
                if "backend_export" not in st.session_state:
                    st.session_state.backend_export = "arquivo"
                indice_backend = opcoes_backend.index(st.session_state.backend_export) if st.session_state.backend_export in opcoes_backend else 0
                backend = st.selectbox("Backend", options=opcoes_backend, index=indice_backend, key="backend_export")
                if backend != st.session_state.backend_export:
                    st.session_state.backend_export = backend
                if backend == "glpi":
                    st.session_state.backend_url = st.text_input("URL do GLPI", value=st.session_state.get("backend_url", ""), key="backend_url")
                    st.session_state.glpi_app_token = st.text_input("App token", value=st.session_state.get("glpi_app_token", ""), key="glpi_app_token")
                    st.session_state.glpi_user_token = st.text_input("User token", value=st.session_state.get("glpi_user_token", ""), key="glpi_user_token")
                    st.session_state.glpi_api_token = st.text_input("Session token", value=st.session_state.get("glpi_api_token", st.session_state.get("glpi_session_token", "")), key="glpi_api_token")
                    st.session_state.glpi_session_token = st.session_state.glpi_api_token
                    st.session_state.glpi_entity_id = st.text_input("Entity ID", value=str(st.session_state.get("glpi_entity_id", 0)), key="glpi_entity_id")
                elif backend == "jira":
                    st.session_state.backend_url = st.text_input("URL do Jira", value=st.session_state.get("backend_url", ""), key="backend_url")
                    st.session_state.jira_user = st.text_input("Usuário Jira", value=st.session_state.get("jira_user", ""), key="jira_user")
                    st.session_state.jira_token = st.text_input("Token Jira", value=st.session_state.get("jira_token", ""), key="jira_token", type="password")
                    st.session_state.jira_password = st.text_input("Senha Jira", value=st.session_state.get("jira_password", ""), key="jira_password", type="password")
                    st.session_state.jira_project_key = st.text_input("Project key", value=st.session_state.get("jira_project_key", "SUP"), key="jira_project_key")
                    st.session_state.jira_issue_type = st.text_input("Issue type", value=st.session_state.get("jira_issue_type", "Task"), key="jira_issue_type")

                payload_backend = _payload_backend(st.session_state.chamado, backend) if backend != "arquivo" else {}
                if payload_backend:
                    with st.expander("Pré-visualização do payload do backend"):
                        st.json(payload_backend)

                if st.button("Enviar para o backend") and backend != "arquivo":
                    try:
                        identificador = _enviar_para_backend(st.session_state.chamado)
                        st.success(f"Chamado enviado ao backend '{backend}' com identificador: {identificador}")
                    except ValueError as erro:
                        st.error(f"Configuração incompleta para {backend}: {erro}")
                        st.info("Preencha a URL, tokens e credenciais do backend antes do envio.")
                    except Exception as erro:  # pragma: no cover - interface de usuário
                        st.error(f"Falha ao enviar para {backend}: {erro}")
                        st.warning("Verifique a conectividade, permissões e credenciais do backend antes de tentar novamente.")

                ultimo_envio = st.session_state.get("ultimo_envio_backend", {})
                if ultimo_envio:
                    st.caption(f"Último envio: {ultimo_envio.get('backend', 'backend')}. ID {ultimo_envio.get('identificador', '—')} · {ultimo_envio.get('timestamp', '')}")

            st.subheader("Modo demo")
            demo_nome = st.selectbox("Cenários fictícios", options=["", *list(DEMO_CENARIOS.keys())], index=0)
            if demo_nome:
                if st.button("Carregar cenário demo"):
                    st.session_state.chamado = carregar_demo(demo_nome)
                    st.session_state.conversa = DEMO_CENARIOS[demo_nome]
                    registrar_historico(st.session_state.chamado)

            arquivo_json = st.file_uploader("Carregar JSON", type=["json"], accept_multiple_files=False)
            if arquivo_json is not None:
                st.session_state.chamado = carregar_chamado_json(arquivo_json)
                st.session_state.conversa = ""
                registrar_historico(st.session_state.chamado)

            arquivo_txt = st.file_uploader("Carregar TXT", type=["txt"], accept_multiple_files=False)
            if arquivo_txt is not None:
                conteudo_txt = arquivo_txt.read().decode("utf-8", errors="replace")
                st.session_state.chamado = carregar_chamado_txt(conteudo_txt)
                st.session_state.conversa = conteudo_txt
                registrar_historico(st.session_state.chamado)
        else:
            consulta = st.text_area(
                "Resumo da conversa / contexto do atendimento",
                value=st.session_state.conversa,
                height=260,
                key="conversa_foco",
            )
            if st.button("Atualizar chamado") and consulta.strip():
                st.session_state.conversa = consulta
                st.session_state.chamado = ExtratorRegras().extrair(consulta, st.session_state.chamado)
                st.session_state.chamado_final = gerar_chamado_final_painel(st.session_state.chamado)
            st.caption("Atendimento focado: atenção ao que falta e à próxima pergunta, sem distrações de demo ou histórico.")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_formulario:
        st.markdown("<div class='section-shell'>", unsafe_allow_html=True)
        st.markdown("<div class='section-tag'>Contexto técnico</div>", unsafe_allow_html=True)
        st.subheader("Dados do chamado")
        formulario = _campos_do_formulario(st.session_state.chamado)
        campos = [
            ("contato_nome", "Nome do contato"),
            ("empresa", "Empresa"),
            ("cnpj", "CNPJ"),
            ("telefone", "Telefone"),
            ("email", "E-mail"),
            ("titulo", "Título"),
            ("tipo", "Tipo"),
            ("prioridade", "Prioridade"),
            ("status", "Status"),
            ("modulo", "Módulo/tela"),
            ("versao", "Versão"),
            ("descricao", "Descrição"),
            ("quando_comecou", "Quando começou"),
            ("mudanca_recente", "Mudança recente"),
            ("escopo", "Escopo"),
            ("dependencias_externas", "Dependências"),
        ]

        col1, col2 = st.columns(2)
        for indice, (campo, rotulo) in enumerate(campos):
            coluna = col1 if indice % 2 == 0 else col2
            with coluna:
                if campo in {"tipo", "prioridade", "status"}:
                    opcoes = {
                        "tipo": ["", "duvida", "bug", "melhoria", "customizacao"],
                        "prioridade": ["", "alta", "media", "baixa"],
                        "status": ["", "aberto", "resolvido", "escalado"],
                    }[campo]
                    valor = formulario[campo] or ""
                    novo = st.selectbox(
                        rotulo,
                        options=opcoes,
                        index=opcoes.index(str(valor)) if str(valor) in opcoes else 0,
                    )
                else:
                    novo = st.text_input(rotulo, value=formulario[campo])
                if novo != formulario[campo]:
                    formulario[campo] = novo

        st.subheader("Contexto técnico")
        col1, col2 = st.columns(2)
        with col1:
            formulario["passos_reproducao"] = st.text_area("Passos para reprodução", value=formulario["passos_reproducao"])
            formulario["evidencias"] = st.text_area("Evidências", value=formulario["evidencias"])
        with col2:
            formulario["recorrente"] = st.checkbox("Recorrente", value=bool(formulario["recorrente"]))
            formulario["telefone_confirmado"] = st.checkbox("Telefone confirmado", value=bool(formulario["telefone_confirmado"]))
            formulario["reproduzido_base_teste"] = st.checkbox("Reproduzido na base de teste", value=bool(formulario["reproduzido_base_teste"]))
            formulario["retorno_ao_cliente_feito"] = st.checkbox("Retorno ao cliente feito", value=bool(formulario["retorno_ao_cliente_feito"]))

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-shell'>", unsafe_allow_html=True)
    st.subheader("Resumo e validação")
    st.session_state.chamado = _atualizar_chamado(st.session_state.chamado, formulario)
    st.session_state.chamado_final = gerar_chamado_final_painel(st.session_state.chamado)
    validacao = validar(st.session_state.chamado, perfil)

    col_nota, col_badge = st.columns([1.2, 2])
    with col_nota:
        st.metric("Nota", f"{validacao.nota}/100")
    with col_badge:
        severidade = classificar_severidade_por_nota(validacao.nota)
        renderizar_badge(severidade, f"Qualidade {severidade}")
        if validacao.sla_horas:
            st.caption(f"SLA estimado: {validacao.sla_horas}h")

    st.subheader("Assistente do analista N1")
    orientacoes = sugestoes_do_assistente(st.session_state.chamado)
    if orientacoes:
        for item in orientacoes[:5]:
            st.markdown(f"- {item}")
    else:
        st.success("Sem bloqueios para o próximo passo; a revisão está pronta para envio.")

    if validacao.pendencias:
        st.warning("Pendências prioritárias")
        for pendencia in validacao.pendencias:
            cor = _cor_badge(pendencia.severidade)
            st.markdown(
                f"<div class='pendencia-card' style='--cor-severidade:{cor};'>"
                f"<div class='pendencia-severidade' style='background:{cor};'>{pendencia.severidade}</div>"
                f"<div><strong>{pendencia.rotulo}</strong> · {pendencia.problema}</div>"
                f"<div style='margin-top:0.4rem;'><em>Pergunte:</em> {pendencia.pergunta}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.success("Registro pronto. Nenhuma pendência crítica foi identificada.")

    if validacao.avisos:
        st.info("Avisos")
        for aviso in validacao.avisos:
            st.write(f"- {aviso}")

    if validacao.pendencias:
        pergunta = validacao.pendencias[0].pergunta
        col_pergunta, col_copia = st.columns([4, 1])
        with col_pergunta:
            st.info(f"Pergunta sugerida: {pergunta}")
        with col_copia:
            if st.button("Copiar pergunta"):
                _copiar_texto_para_area_transferencia(pergunta, "Pergunta sugerida copiada para a área de transferência.")

    st.text_area("Resumo do chamado", value=resumo_texto_limpo(st.session_state.chamado), height=220)

    col_gerar, _ = st.columns([1.25, 3])
    with col_gerar:
        if st.button("Gerar chamado final"):
            st.session_state.chamado_final = gerar_chamado_final_painel(st.session_state.chamado)
            st.toast("Resumo final do chamado atualizado.")

    st.text_area("Chamada final", value=st.session_state.get("chamado_final", gerar_chamado_final_painel(st.session_state.chamado)), height=260)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.modo_focado:
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    _montar_painel()
