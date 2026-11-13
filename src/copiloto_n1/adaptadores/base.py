"""Contrato dos adaptadores de helpdesk. O núcleo só conhece esta interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from copiloto_n1.schemas import Chamado


class AdaptadorHelpdesk(ABC):
    """Um adaptador traduz o `Chamado` neutro para um helpdesk específico (GLPI, Zammad etc.)."""

    @abstractmethod
    def criar_chamado(self, chamado: Chamado) -> str:
        """Registra o chamado e devolve um identificador (número, caminho, URL)."""

    def validar_conexao(self) -> bool:
        """Executa uma checagem simples de autenticidade e conectividade."""
        return True
