"""Fábrica de adaptadores para integração com sistemas externos."""

from __future__ import annotations

import os
from pathlib import Path

from copiloto_n1.adaptadores.arquivo import AdaptadorArquivo
from copiloto_n1.adaptadores.base import AdaptadorHelpdesk
from copiloto_n1.adaptadores.glpi import AdaptadorGLPI
from copiloto_n1.adaptadores.jira import AdaptadorJira


def _valor_ou_default(*candidatos: object) -> str:
    for valor in candidatos:
        if valor is None:
            continue
        texto = str(valor).strip()
        if texto:
            return texto
    return ""


def _carregar_variaveis_env_local() -> None:
    """Carrega variáveis de ambiente a partir do .env do projeto, se existir."""
    raiz = Path(__file__).resolve().parents[3]
    env_path = raiz / ".env"
    if not env_path.exists():
        return

    for linha in env_path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = [parte.strip() for parte in linha.split("=", 1)]
        os.environ.setdefault(chave, valor)


def criar_adaptador(backend: str, **kwargs: object) -> AdaptadorHelpdesk:
    """Cria um adaptador de integração a partir de um backend conhecido."""
    _carregar_variaveis_env_local()
    nome = (backend or "arquivo").lower()
    if nome == "arquivo":
        pasta = str(kwargs.get("pasta", "saida"))
        return AdaptadorArquivo(pasta)
    if nome == "glpi":
        url = _valor_ou_default(kwargs.get("url"), os.getenv("GLPI_URL"))
        app_token = _valor_ou_default(kwargs.get("app_token"), os.getenv("GLPI_APP_TOKEN"))
        user_token = _valor_ou_default(kwargs.get("user_token"), os.getenv("GLPI_USER_TOKEN"))
        api_token = _valor_ou_default(
            kwargs.get("api_token"),
            kwargs.get("session_token"),
            os.getenv("GLPI_API_TOKEN"),
            os.getenv("GLPI_SESSION_TOKEN"),
        )
        entity_id = kwargs.get("entity_id") if kwargs.get("entity_id") is not None else os.getenv("GLPI_ENTITY_ID", "0")
        return AdaptadorGLPI(url=url, app_token=app_token, user_token=user_token, api_token=api_token, entity_id=entity_id)
    if nome == "jira":
        url = _valor_ou_default(kwargs.get("url"), os.getenv("JIRA_URL"))
        user = _valor_ou_default(kwargs.get("user"), os.getenv("JIRA_USER"))
        token = _valor_ou_default(
            kwargs.get("token"),
            kwargs.get("api_token"),
            kwargs.get("password"),
            os.getenv("JIRA_TOKEN"),
            os.getenv("JIRA_API_TOKEN"),
            os.getenv("JIRA_PASSWORD"),
        )
        project_key = _valor_ou_default(kwargs.get("project_key"), os.getenv("JIRA_PROJECT_KEY"), "SUP")
        issue_type = _valor_ou_default(kwargs.get("issue_type"), os.getenv("JIRA_ISSUE_TYPE"), "Task")
        return AdaptadorJira(url=url, user=user, token=token, project_key=project_key, issue_type=issue_type)
    raise ValueError(f"Backend desconhecido: {backend!r}. Use 'arquivo', 'glpi' ou 'jira'.")
