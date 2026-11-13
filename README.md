# Copiloto N1

Assistente **pessoal** para o analista de suporte N1: um **roteiro guiado de perguntas** que conduz o atendimento, aponta o que falta e gera o texto final do chamado para colar em qualquer helpdesk. **Sem LLM**, offline, com os dados ficando no seu dispositivo. O analista continua no controle: a ferramenta sugere, o humano confirma.

> **Direção atual: PWA primeiro** (ver `docs/adr/0003-pwa-first.md`). O código Python deste repositório (validador, perfil, extrator, CLI) é a **especificação de referência** das regras, que serão portadas para o PWA. O app desktop foi arquivado em `legado/desktop/`. Estado: Etapa 1 do PWA pronta (roteiro guiado); veja `docs/backlog.md`.

## Visão geral do produto

O Copiloto N1 foi pensado para apoiar analistas N1 em três momentos:

1. receber uma conversa de atendimento em texto;
2. extrair os dados mais importantes do chamado;
3. validar qualidade do registro com nota, pendências e próxima pergunta.

O fluxo principal é:

```text
conversa (texto) ──► extrator ──► Chamado ──► validador(perfil.yaml) ──► nota + pendências + perguntas
                                      │
                                      └──► export/import JSON/TXT + painel de revisão
```

## Requisitos

- Python 3.11+
- pip
- acesso a terminal

## Instalação

Na raiz do projeto, execute:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

Em Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Rodando a suíte de testes

```bash
pytest
```

## PWA (em construção)

```bash
cd pwa
npm test     # 16 testes: validador (conferido com o Python), motor do roteiro e 3 atendimentos de aceite
npm start    # http://localhost:8080
```

Estado: Etapa 1 (roteiro guiado, uma pergunta por vez) funcionando; o texto final para o Zendesk é a Etapa 2. Perfil e casos de teste são regenerados do Python com `tools/gerar_perfil_json.py` e `tools/gerar_casos_validador.py`.

## Interface

A interface oficial será um **PWA** (HTML/JS estático, instalável, offline). Enquanto ele não existe, as regras podem ser exercitadas pela CLI (`copiloto-n1 validar`, `extrair`, `resumo`).

O painel Streamlit (`copiloto-n1 painel`, requer `pip install -e .[legado]`) é **legado** e sai quando o PWA cobrir o mesmo fluxo. O app desktop PySide6 está em `legado/desktop/` e não é mais evoluído.

## Modo demo

No painel, há uma seção dedicada chamada “Modo demo”, com 3 cenários fictícios:

- impressora
- login
- banco

Esse recurso é útil para testes de apresentação e para validar o fluxo sem preparar uma conversa do zero.

Também é possível carregar um cenário programaticamente:

```python
from copiloto_n1.painel import carregar_demo

chamado = carregar_demo("impressora")
print(chamado.titulo)
```

## CLI

### Validar um chamado

```bash
copiloto-n1 validar examples/chamado_bom.json
copiloto-n1 validar examples/chamado_ruim.json --estrito
```

### Extrair campos da conversa

```bash
copiloto-n1 extrair examples/conversa_exemplo.txt
```

### Gerar resumo legível para revisão

```bash
copiloto-n1 resumo examples/chamado_bom.json
```

### Importar e exportar em JSON/TXT

```bash
copiloto-n1 importar examples/chamado_bom.json --formato json
copiloto-n1 importar examples/conversa_exemplo.txt --formato txt
copiloto-n1 exportar examples/chamado_bom.json saida/chamado.json --formato json
copiloto-n1 exportar examples/chamado_bom.json saida/resumo.txt --formato txt
```

## Fluxo de uso no painel

1. Cole a conversa do atendimento ou carregue um cenário demo.
2. Clique em “Extrair da conversa”.
3. Revise e edite os campos do chamado.
4. A nota e o resumo recalculam em tempo real.
5. Exporte em JSON ou TXT, ou copie o resumo do chamado.

## Estrutura do projeto

```text
docs/            PRD, ADRs, processo de trabalho e backlog
examples/        chamados e conversas fictícias para testes
src/copiloto_n1/ código principal
    __init__.py
    __main__.py
    cli.py
    extrator.py
    painel.py
    perfil.py
    schemas.py
    validador.py
    adaptadores/
tests/           testes automatizados
```

## Principais módulos

- `schemas.py`: o `Chamado`, neutro em relação a qualquer helpdesk.
- `perfil.py`: regras do perfil de qualidade e validações por campo.
- `validador.py`: nota, pendências e pergunta sugerida.
- `extrator.py`: extração por regras a partir da conversa.
- `painel.py`: painel Streamlit (legado) com edição, demo e export/import.
- `cli.py`: interface de linha de comando para uso rápido e integração.

## Privacidade e segurança

- Use somente dados fictícios em exemplos e demonstrações.
- Não grave áudio ou dados sensíveis em ambiente de produção.
- Antes de persistir e exportar em ambientes reais, aplique mascaramento e checagem de dados sensíveis.

## LLM e extração inteligente

O projeto já suporta um fluxo de extração com provider OpenAI-compatible quando a variável de ambiente `OPENAI_API_KEY` estiver configurada.

```bash
export OPENAI_API_KEY="sua-chave"
export OPENAI_BASE_URL="https://api.openai.com/v1/chat/completions"
export OPENAI_MODEL="gpt-4o-mini"
```

Em Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="sua-chave"
$env:OPENAI_BASE_URL="https://api.openai.com/v1/chat/completions"
$env:OPENAI_MODEL="gpt-4o-mini"
```

Se a chave não estiver presente, o sistema usa o fallback local e mantém o fluxo operando sem API.

## Integração com GLPI e Jira

O projeto também permite exportar o chamado final para um backend real de helpdesk usando os adaptadores do pacote `adaptadores`.

Exemplos de uso via CLI:

```bash
copiloto-n1 exportar examples/chamado_bom.json saida/chamado.json --backend glpi \
  --url "https://glpi.exemplo.com" \
  --app-token "APP_TOKEN" \
  --user-token "USER_TOKEN" \
  --entity-id 1

copiloto-n1 exportar examples/chamado_bom.json saida/chamado.json --backend jira \
  --url "https://empresa.atlassian.net" \
  --user "analista@empresa.com" \
  --token "token_ou_api_key" \
  --project-key "SUP"
```

Também é possível preencher as variáveis no arquivo `.env` do projeto:

```bash
GLPI_URL="https://glpi.exemplo.com"
GLPI_APP_TOKEN="..."
GLPI_USER_TOKEN="..."
GLPI_API_TOKEN="..."   # ou GLPI_SESSION_TOKEN
GLPI_SESSION_TOKEN="..."
GLPI_ENTITY_ID=1

JIRA_URL="https://empresa.atlassian.net"
JIRA_USER="analista@empresa.com"
JIRA_TOKEN="..."       # ou JIRA_API_TOKEN
JIRA_API_TOKEN="..."
JIRA_PROJECT_KEY="SUP"
```

## Documentação de negócio e demo

- [docs/pitch-produto.md](docs/pitch-produto.md): visão de negócio, valor e posicionamento.
- [docs/pitch-apresentacao.md](docs/pitch-apresentacao.md): deck de apresentação em slides para stakeholder.
- [docs/proposta-comercial.md](docs/proposta-comercial.md): proposta comercial, modelo de negócio e roadmap.
- [docs/demo-script.md](docs/demo-script.md): roteiro de apresentação em 5 minutos.

## Próximos passos

- Fatia 3: extração por LLM com validação estruturada.
- Integração com API de helpdesk (GLPI, Jira, Zendesk etc.).
- Painel com autenticação e histórico de chamados.
