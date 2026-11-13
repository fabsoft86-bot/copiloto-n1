"""Gera casos "dourados" do validador a partir do Python (especificação de referência).

O validador em JavaScript (pwa/nucleo/validador.js) precisa dar exatamente o mesmo resultado em todos
estes casos. Os dados são fictícios e a geração é determinística (semente fixa).

Uso: PYTHONPATH=src python tools/gerar_casos_validador.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from copiloto_n1.perfil import carregar_perfil
from copiloto_n1.schemas import Chamado
from copiloto_n1.validador import proxima_pergunta, validar

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "pwa" / "tests" / "casos" / "validador.json"
QUANTIDADE_ALEATORIOS = 250

POOL = {
    "contato_nome": [None, "", "   ", "Marina Souza"],
    "empresa": [None, "", "Calçados Exemplo Ltda"],
    "cnpj": [None, "", "11.222.333/0001-81", "11.222.333/0001-82", "11111111111111", "123", "11222333000181"],
    "telefone": [None, "(11) 91234-5678", "1234", "+55 11 91234-5678", "11 3123-4567", "abc"],
    "telefone_confirmado": [None, True, False],
    "email": [None, "a@b.com", "a@b", "sem arroba", "  ", "marina@exemplo.com.br"],
    "titulo": [
        None, "", "erro", "Problema", "Erro ao emitir NFC-e no PDV", "123 456 789 000",
        "ab cd", "  ajuda  ", "teste.", "Sistema lento ao abrir o módulo financeiro", "!!! ??? ...",
    ],
    "tipo": [None, "duvida", "bug", "melhoria", "customizacao"],
    "prioridade": [None, "alta", "media", "baixa"],
    "status": ["aberto", "resolvido", "escalado"],
    "modulo": [None, "", "PDV"],
    "versao": [None, "5.2.1"],
    "descricao": [
        None, "", "Dúvida de como emitir o relatório mensal", "Aparece erro ao salvar o pedido",
        "O sistema travou na tela de vendas", "Preciso de um campo novo no cadastro",
    ],
    "quando_comecou": [None, "Hoje cedo"],
    "recorrente": [None, True, False],
    "mudanca_recente": [None, "nenhuma", "Atualização ontem"],
    "escopo": [None, "Todos os caixas"],
    "dependencias_externas": [None, "Rede ok"],
    "passos_reproducao": [[], ["Abrir o PDV", "Finalizar a venda"]],
    "evidencias": [[], ["print.png"]],
    "reproduzido_base_teste": [None, True, False],
    "causa_raiz": [None, "Certificado vencido"],
    "solucao": [None, "", "Renovado o certificado"],
    "destino_escalonamento": [None, "N2"],
    "retorno_ao_cliente_feito": [None, True, False],
}


def _fixos() -> list[dict]:
    bom = json.loads((RAIZ / "examples" / "chamado_bom.json").read_text(encoding="utf-8"))
    ruim = json.loads((RAIZ / "examples" / "chamado_ruim.json").read_text(encoding="utf-8"))
    return [bom, ruim, {}]


def _aleatorios() -> list[dict]:
    rng = random.Random(2026)
    casos = []
    for _ in range(QUANTIDADE_ALEATORIOS):
        casos.append({campo: rng.choice(opcoes) for campo, opcoes in POOL.items()})
    return casos


def _variacoes_do_bom() -> list[dict]:
    """O chamado bom com UM campo alterado por vez: cobre o cenário 'quase aprovado'."""
    bom = json.loads((RAIZ / "examples" / "chamado_bom.json").read_text(encoding="utf-8"))
    casos = []
    for campo, opcoes in POOL.items():
        for valor in opcoes:
            casos.append({**bom, campo: valor})
    return casos


def main() -> None:
    perfil = carregar_perfil("software_house")
    casos = []
    for entrada in _fixos() + _variacoes_do_bom() + _aleatorios():
        chamado = Chamado(**entrada)
        resultado = validar(chamado, perfil)
        casos.append(
            {
                "chamado": chamado.model_dump(),
                "esperado": {
                    "nota": resultado.nota,
                    "aprovado": resultado.aprovado,
                    "sla_horas": resultado.sla_horas,
                    "avisos": resultado.avisos,
                    "pendencias": [
                        {"campo": p.campo, "severidade": p.severidade, "problema": p.problema}
                        for p in resultado.pendencias
                    ],
                    "proxima_pergunta": proxima_pergunta(resultado),
                },
            }
        )
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(casos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Gerado: {DESTINO.relative_to(RAIZ)} ({len(casos)} casos)")


if __name__ == "__main__":
    main()
