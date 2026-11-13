"""Gera pwa/perfis/software_house.json a partir do perfil YAML (especificação de referência).

`campos` (regras de validação) é copiado fielmente do YAML. O `roteiro` (ordem das perguntas e tipo
de entrada de cada uma) é definido aqui: é a única parte que o PWA acrescenta ao perfil.

Uso: PYTHONPATH=src python tools/gerar_perfil_json.py
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "src" / "copiloto_n1" / "perfis" / "software_house.yaml"
DESTINO = RAIZ / "pwa" / "perfis" / "software_house.json"

TIPOS = [
    {"valor": "duvida", "rotulo": "Dúvida"},
    {"valor": "bug", "rotulo": "Erro do sistema (bug)"},
    {"valor": "melhoria", "rotulo": "Melhoria"},
    {"valor": "customizacao", "rotulo": "Customização"},
]
PRIORIDADES = [
    {"valor": "alta", "rotulo": "Alta: sistema parado"},
    {"valor": "media", "rotulo": "Média: há alternativa"},
    {"valor": "baixa", "rotulo": "Baixa: sem urgência"},
]
STATUS = [
    {"valor": "aberto", "rotulo": "Segue aberto"},
    {"valor": "resolvido", "rotulo": "Resolvido"},
    {"valor": "escalado", "rotulo": "Escalado"},
]

# Ordem em que as perguntas aparecem numa ligação: identificar, classificar cedo (o tipo ramifica o
# resto), entender o problema, e só no fim resumir em um título.
ROTEIRO = [
    {"id": "contato_nome", "entrada": "texto"},
    {"id": "empresa", "entrada": "texto"},
    {"id": "cnpj", "entrada": "texto"},
    {"id": "telefone", "entrada": "telefone"},
    {"id": "tipo", "entrada": "escolha", "opcoes": TIPOS},
    {"id": "descricao", "entrada": "texto_longo"},
    {"id": "modulo", "entrada": "texto"},
    {"id": "versao", "entrada": "texto"},
    {"id": "quando_comecou", "entrada": "texto"},
    {"id": "recorrente", "entrada": "simnao"},
    {"id": "mudanca_recente", "entrada": "texto"},
    {"id": "escopo", "entrada": "texto"},
    {"id": "prioridade", "entrada": "escolha", "opcoes": PRIORIDADES},
    {"id": "passos_reproducao", "entrada": "lista"},
    {"id": "evidencias", "entrada": "lista"},
    {"id": "reproduzido_base_teste", "entrada": "simnao"},
    {"id": "dependencias_externas", "entrada": "texto"},
    {"id": "titulo", "entrada": "texto"},
    {"id": "email", "entrada": "texto"},
    {
        "id": "status",
        "entrada": "escolha",
        "opcoes": STATUS,
        "rotulo": "Situação do atendimento",
        "pergunta": "Como terminou este atendimento?",
    },
    {"id": "causa_raiz", "entrada": "texto_longo"},
    {"id": "solucao", "entrada": "texto_longo"},
    {"id": "destino_escalonamento", "entrada": "texto"},
    {"id": "retorno_ao_cliente_feito", "entrada": "simnao"},
]


def main() -> None:
    dados = yaml.safe_load(ORIGEM.read_text(encoding="utf-8"))
    campos = [
        {
            "id": c["id"],
            "rotulo": c["rotulo"],
            "peso": int(c["peso"]),
            "severidade": c["severidade"],
            "validador": c.get("validador", "presenca"),
            "quando": c.get("quando", "sempre"),
            "pergunta": c["pergunta"],
        }
        for c in dados["campos"]
    ]
    ids_campos = {c["id"] for c in campos}
    ids_roteiro = {p["id"] for p in ROTEIRO}
    faltando = ids_campos - ids_roteiro
    desconhecidos = ids_roteiro - ids_campos - {"status"}
    if faltando or desconhecidos:
        raise SystemExit(f"Roteiro inconsistente com o perfil. Faltando: {faltando}; desconhecidos: {desconhecidos}")

    perfil = {
        "nome": dados["nome"],
        "descricao": dados["descricao"],
        "sla_horas": dados["sla_horas"],
        "titulo": {
            "min_caracteres": dados["titulo"]["min_caracteres"],
            "min_palavras": dados["titulo"]["min_palavras"],
            "genericos": dados["titulo"]["genericos"],
        },
        "palavras_de_erro": dados["palavras_de_erro"],
        "campos": campos,
        "roteiro": ROTEIRO,
    }
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(perfil, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gerado: {DESTINO.relative_to(RAIZ)} ({len(campos)} campos, {len(ROTEIRO)} passos)")


if __name__ == "__main__":
    main()
