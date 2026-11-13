"""Adaptador de integração com Jira Cloud/Data Center via REST."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from copiloto_n1.adaptadores.base import AdaptadorHelpdesk
from copiloto_n1.schemas import Chamado


class AdaptadorJira(AdaptadorHelpdesk):
    """Cria issue de suporte no Jira usando o endpoint REST padronizado."""

    def __init__(
        self,
        url: str | None = None,
        user: str | None = None,
        token: str | None = None,
        password: str | None = None,
        api_token: str | None = None,
        project_key: str | None = None,
        issue_type: str = "Task",
    ) -> None:
        self.url = (url or os.getenv("JIRA_URL", "")).rstrip("/")
        self.user = user or os.getenv("JIRA_USER", "")
        self.token = token or api_token or password or os.getenv("JIRA_TOKEN") or os.getenv("JIRA_API_TOKEN") or os.getenv("JIRA_PASSWORD", "")
        self.project_key = project_key or os.getenv("JIRA_PROJECT_KEY", "SUP")
        self.issue_type = issue_type or os.getenv("JIRA_ISSUE_TYPE", "Task")

        if not self.url:
            raise ValueError("URL do Jira não configurada. Defina JIRA_URL ou passe url=...")
        if not self.user:
            raise ValueError("Usuário do Jira não configurado. Defina JIRA_USER ou passe user=...")
        if not self.token:
            raise ValueError("Token do Jira não configurado. Defina JIRA_TOKEN ou passe token=...")

    def _headers(self) -> dict[str, str]:
        cred = f"{self.user}:{self.token}".encode("utf-8")
        return {
            "Content-Type": "application/json",
            "Authorization": "Basic " + __import__("base64").b64encode(cred).decode("ascii"),
        }

    @staticmethod
    def _prioridade_jira(prioridade: str | None) -> str:
        mapa = {"baixa": "Low", "media": "Medium", "alta": "High"}
        return mapa.get((prioridade or "media").lower(), "Medium")

    def validar_conexao(self) -> bool:
        endpoint = f"{self.url}/rest/api/2/myself"
        req = urllib.request.Request(endpoint, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=20) as resposta:
                return 200 <= resposta.status < 400
        except urllib.error.HTTPError as erro:
            if erro.code in {401, 403}:
                raise RuntimeError("Credenciais do Jira inválidas ou sem permissão.") from erro
            raise RuntimeError(f"Falha ao testar conexão com Jira: {erro}") from erro
        except (urllib.error.URLError, TimeoutError) as erro:
            raise RuntimeError(f"Falha ao testar conexão com Jira: {erro}") from erro

    def criar_chamado(self, chamado: Chamado) -> str:
        if not self.url:
            raise ValueError("URL do Jira não configurada. Defina JIRA_URL ou passe url=...")

        summary = chamado.titulo or "Chamado sem título"
        if chamado.modulo:
            summary = f"[{chamado.modulo}] {summary}"
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": chamado.gerar_chamado_final(),
                "issuetype": {"name": self.issue_type},
                "priority": {"name": self._prioridade_jira(chamado.prioridade)},
                "labels": ["n1", "suporte", "copiloto"],
            }
        }
        endpoint = f"{self.url}/rest/api/2/issue"
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
            raise RuntimeError(f"Falha ao criar issue no Jira: {erro}") from erro

        chave = dados.get("key") or dados.get("id")
        if chave is None:
            raise ValueError(f"Resposta inesperada do Jira: {dados!r}")
        return str(chave)
