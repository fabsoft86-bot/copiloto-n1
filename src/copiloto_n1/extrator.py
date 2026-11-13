"""Extração de campos do chamado a partir da conversa (texto).

Fatia 1/2: extrator por REGRAS (offline, sem API). Fatia 3: extrator por LLM.
O analista confirma tudo: o extrator só preenche o que está vazio (ver `mesclar`).
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Protocol

from copiloto_n1.schemas import Chamado, mesclar


class Extrator(Protocol):
    def extrair(self, conversa: str, atual: Chamado | None = None) -> Chamado:
        """Devolve o chamado com os campos que conseguiu preencher a partir da conversa."""
        ...


_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_TELEFONE = re.compile(r"(?<!\d)\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_NOME = re.compile(
    r"(?i:meu nome é|me chamo|aqui é o|aqui é a|aqui é|sou o|sou a)\s+"
    r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)*)"
)


def _linhas_do_cliente(conversa: str) -> str:
    """Só as falas do cliente, para não confundir com dados que o analista repete."""
    falas = [
        linha.split(":", 1)[1].strip()
        for linha in conversa.splitlines()
        if linha.strip().lower().startswith("cliente:")
    ]
    return "\n".join(falas) if falas else conversa


class ExtratorRegras:
    """Extrai CNPJ, telefone, e-mail e nome por expressões regulares.

    Não define `telefone_confirmado`: confirmar o telefone é um ato do analista.
    """

    def extrair(self, conversa: str, atual: Chamado | None = None) -> Chamado:
        cliente = _linhas_do_cliente(conversa)
        achados: dict[str, str] = {}

        if m := _CNPJ.search(cliente):
            achados["cnpj"] = m.group(0)
        if m := _TELEFONE.search(cliente):
            achados["telefone"] = m.group(0)
        if m := _EMAIL.search(cliente):
            achados["email"] = m.group(0)
        if m := _NOME.search(cliente):
            achados["contato_nome"] = m.group(1)

        novo = Chamado(**achados)
        return mesclar(atual, novo) if atual else novo


def _limpar_json_estruturado(texto: str) -> str:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()
    return texto


def _extrair_json_do_texto(texto: str) -> dict[str, Any] | None:
    texto = _limpar_json_estruturado(texto)
    try:
        dados = json.loads(texto)
        return dados if isinstance(dados, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", texto, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _extrair_json_de_resposta(resposta: Any) -> dict[str, Any] | None:
    """Estratégia permissiva para OpenAI, Anthropic e respostas em formatos similares."""
    if isinstance(resposta, dict):
        if any(chave in resposta for chave in ("titulo", "tipo", "descricao", "contato_nome")):
            return resposta

        for chave in ("content", "message", "output_text", "text", "result"):
            valor = resposta.get(chave)
            if isinstance(valor, str):
                json_extraido = _extrair_json_do_texto(valor)
                if json_extraido:
                    return json_extraido
            if isinstance(valor, list):
                texto = "".join(
                    parte.get("text", "") if isinstance(parte, dict) else str(parte)
                    for parte in valor
                )
                if texto:
                    json_extraido = _extrair_json_do_texto(texto)
                    if json_extraido:
                        return json_extraido
            if isinstance(valor, dict):
                json_extraido = _extrair_json_de_resposta(valor)
                if json_extraido:
                    return json_extraido

        if isinstance(resposta.get("choices"), list):
            for item in resposta["choices"]:
                if not isinstance(item, dict):
                    continue
                message = item.get("message") or item.get("delta") or {}
                json_extraido = _extrair_json_de_resposta(message)
                if json_extraido:
                    return json_extraido

        if isinstance(resposta.get("output"), list):
            for item in resposta["output"]:
                json_extraido = _extrair_json_de_resposta(item)
                if json_extraido:
                    return json_extraido

        texto = resposta.get("text")
        if isinstance(texto, str):
            return _extrair_json_do_texto(texto)
        return None

    if isinstance(resposta, list):
        for item in resposta:
            json_extraido = _extrair_json_de_resposta(item)
            if json_extraido:
                return json_extraido

    if isinstance(resposta, str):
        return _extrair_json_do_texto(resposta)

    return None


class ExtratorLLM:
    """Extrator com validação estruturada e fallback local para uso em produção."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        provider: Callable[[str], dict[str, Any] | None] | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1/chat/completions"
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.provider = provider

    def _fallback_heuristico(self, conversa: str, atual: Chamado | None = None) -> Chamado:
        cliente = _linhas_do_cliente(conversa)
        base = ExtratorRegras().extrair(conversa, atual)
        texto = conversa.lower()

        if "nao consegue" in texto or "não consegue" in texto or "erro de login" in texto:
            base.titulo = base.titulo or "Erro de login"
            base.tipo = base.tipo or "bug"
        if "impressora" in texto or "não imprime" in texto or "nao imprime" in texto:
            base.titulo = base.titulo or "Impressora não imprime"
            base.tipo = base.tipo or "bug"
        if "banco" in texto or "sql" in texto or "falha no banco" in texto:
            base.titulo = base.titulo or "Falha no banco de dados"
            base.tipo = base.tipo or "bug"
        if "versao" in texto or ("v" in texto and re.search(r"v\d+\.\d+", texto)):
            match = re.search(r"vers(?:ã|a)o\s*[: ]*\s*([A-Za-z0-9.]+)", conversa, flags=re.I)
            if match:
                base.versao = match.group(1)
        modulo_match = re.search(
            r"(?:m[óo]dulo|tela|painel|(?:sistema|erp|portal|aplicativo|fluxo))(?:\s+(?:de|do|da))?\s*[: ]?\s*([A-Za-zÀ-ÿ0-9_./\- ]{2,60})",
            conversa,
            flags=re.I,
        )
        if modulo_match and not base.modulo:
            base.modulo = modulo_match.group(1).strip(" .:-")
        if not base.descricao and cliente.strip():
            linhas = [linha.strip() for linha in cliente.splitlines() if linha.strip()]
            base.descricao = linhas[0] if linhas else None
        return base

    def _chamada_provider(self, conversa: str) -> dict[str, Any] | None:
        if self.provider is not None:
            resposta = self.provider(conversa)
            if isinstance(resposta, str):
                return _extrair_json_do_texto(resposta)
            if isinstance(resposta, dict):
                return _extrair_json_de_resposta(resposta) or resposta
            return _extrair_json_de_resposta(resposta)
        if not self.api_key:
            return None

        prompt = (
            "Extraia um chamado de suporte em JSON puro. "
            "Use apenas campos válidos do esquema de chamado: titulo, tipo, prioridade, status, "
            "modulo, versao, descricao, quando_comecou, recorrente, mudanca_recente, escopo, "
            "dependencias_externas, causa_raiz, solucao, destino_escalonamento, "
            "contato_nome, empresa, cnpj, telefone, email, telefone_confirmado, "
            "passos_reproducao, evidencias, reproduzido_base_teste, retorno_ao_cliente_feito. "
            "Responda somente com JSON e sem comentários."
            f"\n\nCONVERSA:\n{conversa}"
        )
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if "anthropic" not in self.base_url.lower():
            payload["response_format"] = {"type": "json_object"}

        body = json.dumps(payload).encode("utf-8")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if "anthropic" in self.base_url.lower():
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = os.getenv("ANTHROPIC_VERSION", "2023-06-01")
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            self.base_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                resposta = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, TimeoutError):
            return None
        return _extrair_json_de_resposta(resposta)

    def extrair(self, conversa: str, atual: Chamado | None = None) -> Chamado:
        """Tenta extrair via provider se configurado; caso contrário usa heurística local."""
        dados = self._chamada_provider(conversa)
        if dados:
            try:
                novo = Chamado.model_validate(dados)
            except Exception:
                novo = self._fallback_heuristico(conversa, atual)
        else:
            novo = self._fallback_heuristico(conversa, atual)
        return mesclar(atual, novo) if atual else novo
