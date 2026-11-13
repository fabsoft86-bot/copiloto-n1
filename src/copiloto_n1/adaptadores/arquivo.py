"""Adaptador mais simples: grava o chamado como JSON em uma pasta."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path

from copiloto_n1.adaptadores.base import AdaptadorHelpdesk
from copiloto_n1.schemas import Chamado


def _slug(texto: str | None) -> str:
    base = unicodedata.normalize("NFKD", texto or "chamado").encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return (base or "chamado")[:50]


class AdaptadorArquivo(AdaptadorHelpdesk):
    def __init__(self, pasta: str | Path = "saida") -> None:
        self.pasta = Path(pasta)

    def criar_chamado(self, chamado: Chamado) -> str:
        self.pasta.mkdir(parents=True, exist_ok=True)
        carimbo = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        caminho = self.pasta / f"{carimbo}_{_slug(chamado.titulo)}.json"
        caminho.write_text(chamado.model_dump_json(indent=2), encoding="utf-8")
        return str(caminho)
