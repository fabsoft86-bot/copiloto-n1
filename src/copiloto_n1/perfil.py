"""Carrega o perfil de qualidade (campos, pesos, perguntas, SLA) a partir de YAML."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

SEVERIDADES = ("bloqueante", "importante", "sugestao")
VALIDADORES = (
    "presenca",
    "verdadeiro",
    "booleano_definido",
    "lista",
    "cnpj",
    "telefone",
    "titulo",
    "email",
)


@dataclass(frozen=True)
class CampoRegra:
    id: str
    rotulo: str
    peso: int
    severidade: str
    pergunta: str
    quando: str = "sempre"
    validador: str = "presenca"


@dataclass(frozen=True)
class Perfil:
    nome: str
    descricao: str
    sla_horas: dict[str, int]
    titulo_min_caracteres: int
    titulo_min_palavras: int
    titulos_genericos: tuple[str, ...]
    palavras_de_erro: tuple[str, ...]
    campos: tuple[CampoRegra, ...]


def _ler_yaml(ref: str | Path) -> dict:
    caminho = Path(ref)
    if caminho.is_file():
        texto = caminho.read_text(encoding="utf-8")
    else:
        recurso = resources.files("copiloto_n1").joinpath("perfis", f"{ref}.yaml")
        if not recurso.is_file():
            raise FileNotFoundError(
                f"Perfil '{ref}' não encontrado (nem como arquivo, nem entre os perfis embutidos)."
            )
        texto = recurso.read_text(encoding="utf-8")
    dados = yaml.safe_load(texto)
    if not isinstance(dados, dict):
        raise ValueError("O perfil deve ser um mapeamento YAML (chave: valor).")
    return dados


def _campo(item: dict, posicao: int) -> CampoRegra:
    for chave in ("id", "rotulo", "peso", "severidade", "pergunta"):
        if chave not in item:
            raise ValueError(f"Campo #{posicao} do perfil sem a chave obrigatória '{chave}'.")
    if item["severidade"] not in SEVERIDADES:
        raise ValueError(
            f"Campo '{item['id']}': severidade '{item['severidade']}' inválida (use {SEVERIDADES})."
        )
    validador = item.get("validador", "presenca")
    if validador not in VALIDADORES:
        raise ValueError(
            f"Campo '{item['id']}': validador '{validador}' desconhecido (use {VALIDADORES})."
        )
    if int(item["peso"]) <= 0:
        raise ValueError(f"Campo '{item['id']}': o peso deve ser maior que zero.")
    return CampoRegra(
        id=item["id"],
        rotulo=item["rotulo"],
        peso=int(item["peso"]),
        severidade=item["severidade"],
        pergunta=item["pergunta"],
        quando=item.get("quando", "sempre"),
        validador=validador,
    )


def carregar_perfil(ref: str | Path = "software_house") -> Perfil:
    """Carrega um perfil pelo nome embutido (ex.: 'software_house') ou por caminho de arquivo."""
    dados = _ler_yaml(ref)
    titulo = dados.get("titulo", {})
    campos = dados.get("campos")
    if not campos:
        raise ValueError("O perfil precisa ter a lista 'campos'.")
    return Perfil(
        nome=dados.get("nome", str(ref)),
        descricao=dados.get("descricao", ""),
        sla_horas={str(k): int(v) for k, v in dados.get("sla_horas", {}).items()},
        titulo_min_caracteres=int(titulo.get("min_caracteres", 15)),
        titulo_min_palavras=int(titulo.get("min_palavras", 3)),
        titulos_genericos=tuple(str(t).lower() for t in titulo.get("genericos", [])),
        palavras_de_erro=tuple(str(p).lower() for p in dados.get("palavras_de_erro", [])),
        campos=tuple(_campo(item, i) for i, item in enumerate(campos, start=1)),
    )
