"""Modelo de dados do chamado, neutro em relação a qualquer helpdesk."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Tipo = Literal["duvida", "bug", "melhoria", "customizacao"]
Prioridade = Literal["alta", "media", "baixa"]
Status = Literal["aberto", "resolvido", "escalado"]


class Chamado(BaseModel):
    """Chamado de suporte. Todos os campos são opcionais: o validador é quem diz o que falta.

    `extra="forbid"` faz um erro de digitação em um JSON virar erro explícito.
    """

    model_config = ConfigDict(extra="forbid")

    # Identificação
    contato_nome: str | None = None
    empresa: str | None = None
    cnpj: str | None = None
    telefone: str | None = None
    telefone_confirmado: bool | None = None
    email: str | None = None

    # Classificação
    titulo: str | None = None
    tipo: Tipo | None = None
    prioridade: Prioridade | None = None
    status: Status = "aberto"

    # Contexto técnico
    modulo: str | None = None
    versao: str | None = None
    descricao: str | None = None
    quando_comecou: str | None = None
    recorrente: bool | None = None
    mudanca_recente: str | None = None
    escopo: str | None = None
    dependencias_externas: str | None = None

    # Reprodução e evidências
    passos_reproducao: list[str] = Field(default_factory=list)
    evidencias: list[str] = Field(default_factory=list)
    reproduzido_base_teste: bool | None = None

    # Desfecho
    causa_raiz: str | None = None
    solucao: str | None = None
    destino_escalonamento: str | None = None
    retorno_ao_cliente_feito: bool | None = None


def _vazio(valor: object) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, list):
        return len(valor) == 0
    return False


def mesclar(atual: Chamado, novo: Chamado) -> Chamado:
    """Preenche só os campos vazios de `atual` com valores de `novo`.

    Regra do produto: a edição humana (valor já preenchido) nunca é sobrescrita
    pela extração automática.
    """
    dados = atual.model_dump()
    for campo, valor in novo.model_dump().items():
        if campo == "status":
            continue  # status é decisão do analista
        if _vazio(dados.get(campo)) and not _vazio(valor):
            dados[campo] = valor
    return Chamado(**dados)


def _valor_ou_vazio(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, list):
        return "\n".join(str(item).strip() for item in valor if str(item).strip())
    return str(valor).strip()


def gerar_relatorio_ticket(chamado: Chamado, validacao: object | None = None) -> str:
    """Gera um relatório em texto simples, pronto para colar em um ticket do Zendesk."""

    def texto(valor: object) -> str:
        if valor is None:
            return "NÃO INFORMADO"
        if isinstance(valor, str):
            return valor.strip() or "NÃO INFORMADO"
        if isinstance(valor, list):
            return "\n".join(str(item).strip() for item in valor if str(item).strip()) or "NÃO INFORMADO"
        return str(valor)

    solicitante = [
        ("Nome", chamado.contato_nome),
        ("Empresa", chamado.empresa),
        ("CNPJ", chamado.cnpj),
        ("Telefone", chamado.telefone),
        ("E-mail", chamado.email),
    ]

    problema = [
        ("Resumo do problema", chamado.descricao),
        ("Título", chamado.titulo),
        ("Tipo", chamado.tipo),
        ("Prioridade", chamado.prioridade),
        ("Módulo / tela", chamado.modulo),
        ("Versão", chamado.versao),
    ]

    passos = chamado.passos_reproducao or ["NÃO INFORMADO"]
    causa = chamado.causa_raiz or "NÃO INFORMADO"
    solucao = chamado.solucao or "NÃO INFORMADO"
    status = chamado.status or "NÃO INFORMADO"

    linhas: list[str] = []
    linhas.append("Solicitante")
    for label, valor in solicitante:
        linhas.append(f"{label}: {texto(valor)}")
    linhas.append("")

    linhas.append("Resumo do problema")
    for label, valor in problema:
        linhas.append(f"{label}: {texto(valor)}")
    linhas.append("")

    linhas.append("Passos realizados")
    if isinstance(passos, list):
        for i, item in enumerate(passos, start=1):
            linhas.append(f"{i}. {texto(item)}")
    else:
        linhas.append(texto(passos))
    linhas.append("")

    linhas.append("Causa identificada")
    linhas.append(texto(causa))
    linhas.append("")

    linhas.append("Solução aplicada")
    linhas.append(texto(solucao))
    linhas.append("")

    linhas.append("Status")
    linhas.append(f"{texto(status)}")
    linhas.append("")

    linhas.append("Próximo passo / pendências")
    if validacao is not None and getattr(validacao, "pendencias", None):
        for item in validacao.pendencias:
            linhas.append(f"- {item.rotulo}: {item.pergunta}")
    else:
        linhas.append("NÃO INFORMADO")

    return "\n".join(linhas)


def gerar_chamado_final(chamado: Chamado) -> str:
    """Gera um resumo textual legível do chamado, pronto para revisão humana.

    O texto combina os campos mais úteis para o analista e para a triagem do N2/N3.
    """
    linhas: list[str] = []

    cabecalho = [
        f"Título: {chamado.titulo or 'Não informado'}",
        f"Tipo: {chamado.tipo or 'Não informado'}",
        f"Prioridade: {chamado.prioridade or 'Não informada'}",
        f"Status: {chamado.status or 'Não informado'}",
    ]
    linhas.append("\n".join(cabecalho))

    info = []
    if chamado.contato_nome:
        info.append(f"Contato: {chamado.contato_nome}")
    if chamado.empresa:
        info.append(f"Empresa: {chamado.empresa}")
    if chamado.cnpj:
        info.append(f"CNPJ: {chamado.cnpj}")
    if chamado.telefone:
        info.append(f"Telefone: {chamado.telefone}")
    if chamado.email:
        info.append(f"E-mail: {chamado.email}")
    if info:
        linhas.append("\n".join(info))

    if chamado.descricao:
        linhas.append(f"Descrição:\n{chamado.descricao}")
    detalhes = []
    for campo, label in (
        (chamado.modulo, "Módulo/tela"),
        (chamado.versao, "Versão"),
        (chamado.quando_comecou, "Quando começou"),
        (chamado.mudanca_recente, "Mudança recente"),
        (chamado.escopo, "Abrangência"),
        (chamado.dependencias_externas, "Dependências externas"),
    ):
        if campo:
            detalhes.append(f"- {label}: {campo}")
    if detalhes:
        linhas.append("Detalhes do contexto:\n" + "\n".join(detalhes))

    if chamado.passos_reproducao:
        linhas.append(
            "Passos para reprodução:\n" + "\n".join(f"{i}. {p}" for i, p in enumerate(chamado.passos_reproducao, 1))
        )
    if chamado.evidencias:
        linhas.append("Evidências:\n" + "\n".join(f"- {item}" for item in chamado.evidencias))
    if chamado.reproduzido_base_teste is not None:
        linhas.append(f"Reproduzido na base de teste: {'sim' if chamado.reproduzido_base_teste else 'não'}")
    if chamado.causa_raiz:
        linhas.append(f"Causa raiz:\n{chamado.causa_raiz}")
    if chamado.solucao:
        linhas.append(f"Solução aplicada:\n{chamado.solucao}")
    if chamado.destino_escalonamento:
        linhas.append(f"Destino do escalonamento:\n{chamado.destino_escalonamento}")

    return "\n\n".join(linha for linha in linhas if linha.strip())


Chamado.gerar_chamado_final = gerar_chamado_final
Chamado.__str__ = lambda self: gerar_chamado_final(self)
