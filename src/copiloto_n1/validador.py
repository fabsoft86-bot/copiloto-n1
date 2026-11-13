"""Validador de qualidade do chamado: nota, pendências e pergunta sugerida para cada uma."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from copiloto_n1.perfil import CampoRegra, Perfil
from copiloto_n1.schemas import Chamado

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Pendencia:
    campo: str
    rotulo: str
    severidade: str
    problema: str
    pergunta: str


@dataclass
class Resultado:
    nota: int
    pendencias: list[Pendencia] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    sla_horas: int | None = None

    @property
    def bloqueantes(self) -> list[Pendencia]:
        return [p for p in self.pendencias if p.severidade == "bloqueante"]

    @property
    def aprovado(self) -> bool:
        return not self.bloqueantes


# --------------------------------------------------------------------------- condições


def condicao_atendida(quando: str, chamado: Chamado) -> bool:
    """Avalia 'sempre' ou 'campo=valor1|valor2' contra o chamado."""
    quando = quando.strip()
    if quando == "sempre":
        return True
    if "=" not in quando:
        raise ValueError(f"Condição inválida no perfil: '{quando}'.")
    campo, _, valores = quando.partition("=")
    atual = getattr(chamado, campo.strip(), None)
    return str(atual) in {v.strip() for v in valores.split("|")}


# --------------------------------------------------------------------------- validadores


def _texto_vazio(valor: object) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def cnpj_valido(cnpj: str) -> bool:
    digitos = re.sub(r"\D", "", cnpj)
    if len(digitos) != 14 or len(set(digitos)) == 1:
        return False

    def digito(base: str, pesos: list[int]) -> str:
        resto = sum(int(d) * p for d, p in zip(base, pesos)) % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = digito(digitos[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = digito(digitos[:12] + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digitos[12:] == d1 + d2


def _checar_titulo(titulo: str | None, perfil: Perfil) -> str | None:
    if _texto_vazio(titulo):
        return "título ausente"
    t = titulo.strip()
    if not re.search(r"[A-Za-zÀ-ÿ]", t):
        return "o título não tem texto (só símbolos ou números)"
    if t.lower().strip(" .:-") in perfil.titulos_genericos:
        return f"título genérico ('{t}'): não permite achar o chamado depois"
    if len(t) < perfil.titulo_min_caracteres or len(t.split()) < perfil.titulo_min_palavras:
        return (
            f"título curto demais (mínimo {perfil.titulo_min_caracteres} caracteres e "
            f"{perfil.titulo_min_palavras} palavras)"
        )
    return None


def _checar_campo(regra: CampoRegra, chamado: Chamado, perfil: Perfil) -> str | None:
    """Devolve a descrição do problema, ou None se o campo está ok."""
    valor = getattr(chamado, regra.id, None)
    v = regra.validador

    if v == "presenca":
        return "não informado" if _texto_vazio(valor) else None
    if v == "lista":
        return "nenhum item informado" if not valor else None
    if v == "booleano_definido":
        return "não informado" if valor is None else None
    if v == "verdadeiro":
        return "ainda não feito/confirmado" if valor is not True else None
    if v == "cnpj":
        if _texto_vazio(valor):
            return "não informado"
        return None if cnpj_valido(valor) else "CNPJ inválido (confira os dígitos)"
    if v == "telefone":
        if _texto_vazio(valor):
            return "não informado"
        digitos = re.sub(r"\D", "", valor)
        if digitos.startswith("55") and len(digitos) > 11:
            digitos = digitos[2:]
        if len(digitos) not in (10, 11):
            return "telefone com número de dígitos inválido (use DDD + número)"
        if chamado.telefone_confirmado is not True:
            return "telefone ainda não confirmado com o cliente"
        return None
    if v == "titulo":
        return _checar_titulo(valor, perfil)
    if v == "email":
        if _texto_vazio(valor):
            return "não informado"
        return None if _EMAIL.match(valor.strip()) else "e-mail em formato inválido"
    raise ValueError(f"Validador desconhecido: {v}")  # protegido também em perfil.py


# --------------------------------------------------------------------------- avisos


def _avisos(chamado: Chamado, perfil: Perfil) -> list[str]:
    avisos: list[str] = []
    texto = f"{chamado.titulo or ''} {chamado.descricao or ''}".lower()
    if chamado.tipo == "duvida" and any(p in texto for p in perfil.palavras_de_erro):
        avisos.append(
            "Marcado como dúvida, mas o texto menciona erro/falha. Confirme se não é um bug "
            "(classificação errada distorce relatórios e atrasa o N2)."
        )
    if chamado.tipo == "bug" and chamado.reproduzido_base_teste is False and chamado.evidencias == []:
        avisos.append("Bug não reproduzido na base de teste e sem evidência: o N2 terá dificuldade em investigar.")
    return avisos


# --------------------------------------------------------------------------- API


def validar(chamado: Chamado, perfil: Perfil) -> Resultado:
    """Valida o chamado. A nota é proporcional ao peso dos campos que se aplicam a ele."""
    aplicavel = 0
    ganho = 0
    pendencias: list[Pendencia] = []

    for regra in perfil.campos:
        if not condicao_atendida(regra.quando, chamado):
            continue
        aplicavel += regra.peso
        problema = _checar_campo(regra, chamado, perfil)
        if problema is None:
            ganho += regra.peso
        else:
            pendencias.append(
                Pendencia(regra.id, regra.rotulo, regra.severidade, problema, regra.pergunta)
            )

    nota = round(100 * ganho / aplicavel) if aplicavel else 100
    ordem = {"bloqueante": 0, "importante": 1, "sugestao": 2}
    pendencias.sort(key=lambda p: ordem[p.severidade])

    sla = perfil.sla_horas.get(chamado.prioridade) if chamado.prioridade else None
    return Resultado(nota=nota, pendencias=pendencias, avisos=_avisos(chamado, perfil), sla_horas=sla)


def proxima_pergunta(resultado: Resultado) -> str | None:
    """A pergunta da pendência mais grave (ou None se não há pendências)."""
    return resultado.pendencias[0].pergunta if resultado.pendencias else None
