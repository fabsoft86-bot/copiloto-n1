"""Adaptador de integração com GLPI via API REST."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from copiloto_n1.adaptadores.base import AdaptadorHelpdesk
from copiloto_n1.schemas import Chamado


class AdaptadorGLPI(AdaptadorHelpdesk):
    """Cria tickets em GLPI através da API REST do sistema."""

    def __init__(
        self,
        url: str,
        app_token: str,
        user_token: str,
        api_token: str | None = None,
        session_token: str | None = None,
        entity_id: int | str = 0,
    ) -> None:
        self.url = url.rstrip("/")
        self.app_token = app_token
        self.user_token = user_token
        self.api_token = api_token or session_token
        self.entity_id = entity_id

        if not self.url:
            raise ValueError("URL do GLPI não configurada. Defina GLPI_URL ou passe url=...")
        if not self.app_token:
            raise ValueError("App token do GLPI não configurado. Defina GLPI_APP_TOKEN ou passe app_token=...")
        if not self.user_token:
            raise ValueError("User token do GLPI não configurado. Defina GLPI_USER_TOKEN ou passe user_token=...")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Authorization": f"user_token {self.user_token}",
        }
        if self.api_token:
            headers["Session-Token"] = self.api_token
        return headers

    @staticmethod
    def _prioridade_glpi(prioridade: str | None) -> tuple[int, int]:
        mapa = {
            "baixa": (2, 3),
            "media": (3, 2),
            "alta": (4, 1),
        }
        return mapa.get((prioridade or "media").lower(), (3, 2))

    def validar_conexao(self) -> bool:
        endpoint = f"{self.url}/apirest.php/Ticket?limit=1"
        req = urllib.request.Request(endpoint, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=20) as resposta:
                return 200 <= resposta.status < 400
        except urllib.error.HTTPError as erro:
            if erro.code in {401, 403}:
                raise RuntimeError("Credenciais do GLPI inválidas ou sem permissão.") from erro
            raise RuntimeError(f"Falha ao testar conexão com GLPI: {erro}") from erro
        except (urllib.error.URLError, TimeoutError) as erro:
            raise RuntimeError(f"Falha ao testar conexão com GLPI: {erro}") from erro

    def criar_chamado(self, chamado: Chamado) -> str:
        urgencia, prioridade = self._prioridade_glpi(chamado.prioridade)
        nome = chamado.titulo or "Chamado sem título"
        if chamado.modulo:
            nome = f"[{chamado.modulo}] {nome}"
        payload = {
            "input": {
                "name": nome,
                "content": chamado.gerar_chamado_final(),
                "status": 1,
                "urgency": urgencia,
                "priority": prioridade,
                "type": 1,
                "entities_id": int(self.entity_id),
            }
        }
        endpoint = f"{self.url}/apirest.php/Ticket"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, TimeoutError) as erro:
            raise RuntimeError(f"Falha ao criar ticket no GLPI: {erro}") from erro

        if isinstance(dados, dict):
            ticket_id = dados.get("id") or dados.get("ticket", {}).get("id")
            if ticket_id is not None:
                return str(ticket_id)
        raise ValueError(f"Resposta inesperada do GLPI: {dados!r}")
