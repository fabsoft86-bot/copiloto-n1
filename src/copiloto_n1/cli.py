"""Linha de comando: validar, extrair, resumir e exportar chamados."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from pydantic import ValidationError

from copiloto_n1.adaptadores import criar_adaptador
from copiloto_n1.extrator import ExtratorRegras
from copiloto_n1.perfil import carregar_perfil
from copiloto_n1.schemas import Chamado
from copiloto_n1.validador import Resultado, proxima_pergunta, validar

_MARCA = {"bloqueante": "✗ BLOQUEANTE", "importante": "! importante ", "sugestao": "· sugestão   "}


def _imprimir_resultado(res: Resultado, perfil_nome: str) -> None:
    sla = f"{res.sla_horas}h" if res.sla_horas else "—"
    print(f"Perfil: {perfil_nome}  |  Nota: {res.nota}/100  |  SLA da prioridade: {sla}")
    if not res.pendencias and not res.avisos:
        print("\nChamado completo. Nada a corrigir.")
    for p in res.pendencias:
        print(f"\n{_MARCA[p.severidade]}  {p.rotulo} — {p.problema}")
        print(f'   ↳ Pergunte: "{p.pergunta}"')
    if res.avisos:
        print("\nAvisos:")
        for aviso in res.avisos:
            print(f"  - {aviso}")
    pergunta = proxima_pergunta(res)
    if pergunta:
        print(f'\nPróxima pergunta sugerida: "{pergunta}"')
    n = len(res.bloqueantes)
    print(f"\nResultado: {'APROVADO' if res.aprovado else f'REPROVADO ({n} bloqueante(s))'}")


def _cmd_validar(args: argparse.Namespace) -> int:
    perfil = carregar_perfil(args.perfil)
    chamado = Chamado.model_validate_json(Path(args.arquivo).read_text(encoding="utf-8"))
    res = validar(chamado, perfil)
    _imprimir_resultado(res, perfil.nome)
    return 1 if (args.estrito and not res.aprovado) else 0


def _cmd_extrair(args: argparse.Namespace) -> int:
    perfil = carregar_perfil(args.perfil)
    conversa = Path(args.arquivo).read_text(encoding="utf-8")
    chamado = ExtratorRegras().extrair(conversa)
    print("Campos extraídos (regras):")
    achados = {k: v for k, v in chamado.model_dump(exclude_defaults=True).items()}
    print(json.dumps(achados, ensure_ascii=False, indent=2) if achados else "  (nenhum)")
    print()
    _imprimir_resultado(validar(chamado, perfil), perfil.nome)
    if args.saida:
        Path(args.saida).write_text(chamado.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nChamado parcial salvo em {args.saida} (complete e rode `validar`).")
    return 0


def _cmd_resumo(args: argparse.Namespace) -> int:
    chamado = Chamado.model_validate_json(Path(args.arquivo).read_text(encoding="utf-8"))
    print(chamado.gerar_chamado_final())
    return 0


def _cmd_importar(args: argparse.Namespace) -> int:
    from copiloto_n1.painel import carregar_chamado_json, carregar_chamado_txt

    origem = Path(args.arquivo)
    if args.formato == "json":
        chamado = carregar_chamado_json(origem)
    else:
        chamado = carregar_chamado_txt(origem)
    print(json.dumps(chamado.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


def _cmd_exportar(args: argparse.Namespace) -> int:
    from copiloto_n1.painel import salvar_chamado_json, salvar_chamado_txt

    chamado = Chamado.model_validate_json(Path(args.arquivo).read_text(encoding="utf-8"))
    if args.backend and args.backend.lower() != "arquivo":
        kwargs = {
            "url": args.url,
            "app_token": args.app_token,
            "user_token": args.user_token,
            "api_token": args.api_token or args.session_token,
            "session_token": args.session_token,
            "entity_id": args.entity_id,
            "user": args.user,
            "token": args.token,
            "password": args.password,
            "project_key": args.project_key,
            "issue_type": args.issue_type,
            "pasta": args.saida,
        }
        adaptador = criar_adaptador(args.backend, **kwargs)
        identificador = adaptador.criar_chamado(chamado)
        print(f"Chamado enviado ao backend '{args.backend}' com identificador: {identificador}")
        return 0

    destino = Path(args.saida)
    if args.formato == "json":
        caminho = salvar_chamado_json(chamado, destino)
    else:
        caminho = salvar_chamado_txt(chamado, destino)
    print(f"Arquivo gerado em: {caminho}")
    return 0


def _cmd_painel(args: argparse.Namespace) -> int:
    script = Path(__file__).resolve().with_name("painel.py")
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(script),
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
            ],
            check=False,
        )
        return completed.returncode
    except FileNotFoundError:
        print("Erro: streamlit não está instalado no ambiente atual.", file=sys.stderr)
        return 2


def _cmd_desktop(args: argparse.Namespace) -> int:
    from copiloto_n1.desktop_app import main as desktop_main
    return desktop_main()


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="copiloto-n1", description=__doc__)
    sub = p.add_subparsers(dest="comando", required=True)

    v = sub.add_parser("validar", help="valida um chamado em JSON")
    v.add_argument("arquivo", help="caminho do JSON do chamado")
    v.add_argument("--perfil", default="software_house", help="nome do perfil embutido ou caminho de um YAML")
    v.add_argument("--estrito", action="store_true", help="sai com código 1 se houver pendência bloqueante")
    v.set_defaults(func=_cmd_validar)

    e = sub.add_parser("extrair", help="extrai campos de uma conversa em texto (Analista:/Cliente:)")
    e.add_argument("arquivo", help="caminho do .txt com a conversa")
    e.add_argument("--perfil", default="software_house")
    e.add_argument("--saida", help="salva o chamado parcial (JSON) neste caminho")
    e.set_defaults(func=_cmd_extrair)

    r = sub.add_parser("resumo", help="gera texto legível do chamado para revisão e envio")
    r.add_argument("arquivo", help="caminho do JSON do chamado")
    r.set_defaults(func=_cmd_resumo)

    i = sub.add_parser("importar", help="carrega um chamado em JSON ou texto de conversa")
    i.add_argument("arquivo", help="caminho do arquivo de origem")
    i.add_argument("--formato", choices=["json", "txt"], default="json", help="tipo de fonte de entrada")
    i.set_defaults(func=_cmd_importar)

    x = sub.add_parser("exportar", help="exporta o chamado para JSON/TXT ou envia para backend de helpdesk")
    x.add_argument("arquivo", help="caminho do JSON do chamado")
    x.add_argument("saida", help="caminho do destino ou pasta para arquivo local")
    x.add_argument("--formato", choices=["json", "txt"], default="json", help="tipo de saída desejada")
    x.add_argument("--backend", choices=["arquivo", "glpi", "jira"], default="arquivo", help="backend de destino")
    x.add_argument("--url", help="URL do backend (GLPI/Jira)")
    x.add_argument("--app-token", help="App token do GLPI")
    x.add_argument("--user-token", help="User token do GLPI")
    x.add_argument("--api-token", help="Session token opcional do GLPI")
    x.add_argument("--session-token", help="Alias do token de sessão do GLPI")
    x.add_argument("--entity-id", help="Entity ID do GLPI")
    x.add_argument("--user", help="Usuário do Jira")
    x.add_argument("--token", help="Token do Jira")
    x.add_argument("--password", help="Senha do Jira (alternativa ao token)")
    x.add_argument("--project-key", help="Project Key do Jira")
    x.add_argument("--issue-type", help="Tipo de issue do Jira")
    x.set_defaults(func=_cmd_exportar)

    pnr = sub.add_parser("painel", help="abre o painel Streamlit para editar o chamado em tempo real")
    pnr.set_defaults(func=_cmd_painel)

    desktop = sub.add_parser("desktop", help="abre a aplicação desktop nativa do N1 Flow")
    desktop.set_defaults(func=_cmd_desktop)
    return p


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = ["desktop"]
    elif not argv:
        argv = ["desktop"]
    args = _parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, ValidationError, RuntimeError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
