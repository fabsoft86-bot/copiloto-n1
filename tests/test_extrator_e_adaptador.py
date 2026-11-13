import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

from copiloto_n1.adaptadores import AdaptadorArquivo, AdaptadorGLPI, AdaptadorJira, criar_adaptador
from copiloto_n1.cli import main
from copiloto_n1.extrator import ExtratorLLM, ExtratorRegras
from copiloto_n1.schemas import Chamado, mesclar

EXEMPLOS = Path(__file__).resolve().parent.parent / "examples"


def _conversa() -> str:
    return (EXEMPLOS / "conversa_exemplo.txt").read_text(encoding="utf-8")


def test_extrator_encontra_cnpj_telefone_email_e_nome_sem_internet():
    c = ExtratorRegras().extrair(_conversa())
    assert c.cnpj == "11.222.333/0001-81"
    assert c.telefone == "(11) 91234-5678"
    assert c.email == "marina.souza@exemplo.com.br"
    assert c.contato_nome == "Marina Souza"


def test_extrator_nao_confirma_telefone_sozinho():
    assert ExtratorRegras().extrair(_conversa()).telefone_confirmado is None


def test_extracao_nunca_sobrescreve_edicao_humana():
    atual = Chamado(contato_nome="Marina S. (editado)", telefone=None)
    c = ExtratorRegras().extrair(_conversa(), atual)
    assert c.contato_nome == "Marina S. (editado)"  # preservado
    assert c.telefone == "(11) 91234-5678"  # vazio foi preenchido


def test_mesclar_nao_altera_status():
    assert mesclar(Chamado(status="escalado"), Chamado(status="resolvido")).status == "escalado"


def test_extrator_llm_fallback_heuristico_extrai_titulo_e_tipo():
    chamado = ExtratorLLM().extrair(
        "Cliente: meu nome é Ana, não consigo entrar no sistema e aparece erro de login após a atualização."
    )
    assert chamado.tipo == "bug"
    assert "login" in (chamado.titulo or "").lower()


def test_extrator_llm_aceita_provider_customizado():
    def fake_provider(conversa: str):
        assert "cliente" in conversa.lower()
        return {"titulo": "Erro ao fazer login", "tipo": "bug", "descricao": "Sistema bloqueia acesso."}

    chamado = ExtratorLLM(provider=fake_provider).extrair("Cliente: não consigo entrar no sistema")
    assert chamado.titulo == "Erro ao fazer login"
    assert chamado.tipo == "bug"


def test_extrator_llm_extrai_modulo_versao_e_descricao_do_provider():
    def fake_provider(conversa: str):
        return {
            "titulo": "Erro ao emitir NFC-e",
            "tipo": "bug",
            "modulo": "Faturamento",
            "versao": "4.8.1",
            "descricao": "Ao clicar em emitir, o sistema trava.",
        }

    chamado = ExtratorLLM(provider=fake_provider).extrair("Cliente: não imprime o documento na tela de faturamento")
    assert chamado.tipo == "bug"
    assert chamado.modulo == "Faturamento"
    assert chamado.versao == "4.8.1"
    assert "sistema trava" in (chamado.descricao or "").lower()


def test_extrator_llm_envia_bearer_token_corretamente(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({
                "choices": [{
                    "message": {
                        "content": "```json\n{\"titulo\": \"Erro de login\", \"tipo\": \"bug\", \"descricao\": \"Sistema bloqueia acesso\"}\n```"
                    }
                }]
            }).encode("utf-8")

    captured = {}

    def fake_urlopen(req, timeout=30):
        captured["authorization"] = req.headers.get("Authorization")
        return FakeResponse({})

    monkeypatch.setattr("copiloto_n1.extrator.urllib.request.urlopen", fake_urlopen)
    chamado = ExtratorLLM(api_key="sk-test-123", base_url="https://api.example.com/v1/chat/completions").extrair(
        "Cliente: não consigo entrar no sistema"
    )

    assert captured["authorization"] == "Bearer sk-test-123"
    assert chamado.titulo == "Erro de login"
    assert chamado.tipo == "bug"


def test_extrator_llm_parseia_resposta_com_lista_de_texto():
    resposta = {
        "content": [
            {"type": "text", "text": "```json\n{\"titulo\": \"Falha de banco\", \"tipo\": \"bug\"}\n```"}
        ]
    }
    assert ExtratorLLM(provider=lambda _: resposta).extrair("Cliente: está falhando o banco").titulo == "Falha de banco"


def test_adaptador_de_arquivo_grava_json_legivel(tmp_path):
    chamado = Chamado(titulo="Erro ao emitir NFC-e no PDV", contato_nome="Marina")
    caminho = AdaptadorArquivo(tmp_path / "saida").criar_chamado(chamado)
    gravado = json.loads(Path(caminho).read_text(encoding="utf-8"))
    assert gravado["titulo"] == "Erro ao emitir NFC-e no PDV"
    assert "erro-ao-emitir-nfc-e-no-pdv" in Path(caminho).name


def test_gerar_chamado_final_traz_detalhes_essenciais():
    chamado = Chamado(
        titulo="Erro ao emitir NFC-e no PDV",
        tipo="bug",
        descricao="Ao clicar em emitir, o sistema trava e fecha o cliente.",
        passos_reproducao=["Abre o PDV", "Clica em emitir", "Sistema fecha"],
        evidencias=["print_001.png"],
        solucao="Reinstalei a biblioteca de NFC-e e atualizei o certificado.",
    )
    texto = chamado.gerar_chamado_final()
    assert "Erro ao emitir NFC-e no PDV" in texto
    assert "Ao clicar em emitir" in texto
    assert "Passos para reprodução" in texto
    assert "print_001.png" in texto
    assert "Solução aplicada" in texto


def test_adaptador_glpi_cria_ticket():
    class Handler(BaseHTTPRequestHandler):
        payload = {}

        def do_POST(self):
            comprimento = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(comprimento)
            self.server.payload = json.loads(body.decode("utf-8"))
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": 4321}).encode("utf-8"))

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    porta = server.server_address[1]
    server.payload = {}
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        adaptador = AdaptadorGLPI(f"http://127.0.0.1:{porta}", "app", "user", "session", entity_id=7)
        ticket_id = adaptador.criar_chamado(Chamado(titulo="Erro de login", prioridade="alta", descricao="Não entra no sistema."))
        assert ticket_id == "4321"
        assert server.payload["input"]["name"] == "Erro de login"
        assert server.payload["input"]["priority"] == 1
        assert server.payload["input"]["urgency"] == 4
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_adaptador_jira_cria_issue():
    class Handler(BaseHTTPRequestHandler):
        payload = {}

        def do_POST(self):
            comprimento = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(comprimento)
            self.server.payload = json.loads(body.decode("utf-8"))
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"key": "N1-188"}).encode("utf-8"))

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    porta = server.server_address[1]
    server.payload = {}
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        adaptador = AdaptadorJira(f"http://127.0.0.1:{porta}", "usuario", "segredo", project_key="N1", issue_type="Task")
        issue_id = adaptador.criar_chamado(Chamado(titulo="Falha de login", prioridade="media", descricao="Erro ao autenticar."))
        assert issue_id == "N1-188"
        assert server.payload["fields"]["project"]["key"] == "N1"
        assert server.payload["fields"]["priority"]["name"] == "Medium"
        assert "n1" in server.payload["fields"]["labels"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_adaptador_validar_conexao_aceita_200_e_recusa_401():
    class HandlerOK(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, format, *args):
            return

    server_ok = HTTPServer(("127.0.0.1", 0), HandlerOK)
    porta_ok = server_ok.server_address[1]
    thread_ok = Thread(target=server_ok.serve_forever, daemon=True)
    thread_ok.start()

    try:
        assert AdaptadorJira(f"http://127.0.0.1:{porta_ok}", "usuario", "segredo").validar_conexao() is True
        assert AdaptadorGLPI(f"http://127.0.0.1:{porta_ok}", "app", "user", "session").validar_conexao() is True
    finally:
        server_ok.shutdown()
        server_ok.server_close()
        thread_ok.join(timeout=5)

    class HandlerAuth(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "unauthorized"}')

        def log_message(self, format, *args):
            return

    server_auth = HTTPServer(("127.0.0.1", 0), HandlerAuth)
    porta_auth = server_auth.server_address[1]
    thread_auth = Thread(target=server_auth.serve_forever, daemon=True)
    thread_auth.start()

    try:
        try:
            AdaptadorJira(f"http://127.0.0.1:{porta_auth}", "usuario", "segredo").validar_conexao()
            raise AssertionError("validar_conexao() deveria falhar para 401")
        except RuntimeError as erro:
            assert "Credenciais do Jira inválidas" in str(erro)

        try:
            AdaptadorGLPI(f"http://127.0.0.1:{porta_auth}", "app", "user", "session").validar_conexao()
            raise AssertionError("validar_conexao() deveria falhar para 401")
        except RuntimeError as erro:
            assert "Credenciais do GLPI inválidas" in str(erro)
    finally:
        server_auth.shutdown()
        server_auth.server_close()
        thread_auth.join(timeout=5)


def test_criar_adaptador_por_fabrica():
    assert isinstance(criar_adaptador("arquivo", pasta="saida"), AdaptadorArquivo)
    assert isinstance(criar_adaptador("glpi", url="http://example.com", app_token="a", user_token="b", api_token="c"), AdaptadorGLPI)
    assert isinstance(criar_adaptador("glpi", url="http://example.com", app_token="a", user_token="b", session_token="c"), AdaptadorGLPI)
    assert isinstance(criar_adaptador("jira", url="http://example.com", user="u", token="t", project_key="SUP"), AdaptadorJira)


def test_factory_aceita_variaveis_alias_do_glpi_e_jira(monkeypatch):
    monkeypatch.setenv("GLPI_URL", "http://example.com")
    monkeypatch.setenv("GLPI_APP_TOKEN", "app")
    monkeypatch.setenv("GLPI_USER_TOKEN", "user")
    monkeypatch.setenv("GLPI_SESSION_TOKEN", "session")
    monkeypatch.setenv("JIRA_URL", "http://jira.example.com")
    monkeypatch.setenv("JIRA_USER", "analista")
    monkeypatch.setenv("JIRA_API_TOKEN", "jira-token")

    glpi = criar_adaptador("glpi")
    jira = criar_adaptador("jira")

    assert isinstance(glpi, AdaptadorGLPI)
    assert isinstance(jira, AdaptadorJira)
    assert glpi.api_token == "session"
    assert jira.token == "jira-token"


def test_cli_exportar_backend_glpi(capsys):
    class Handler(BaseHTTPRequestHandler):
        payload = {}

        def do_POST(self):
            comprimento = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(comprimento)
            self.server.payload = json.loads(body.decode("utf-8"))
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": 99}).encode("utf-8"))

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    porta = server.server_address[1]
    server.payload = {}
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        arquivo = EXEMPLOS / "chamado_bom.json"
        assert main([
            "exportar",
            str(arquivo),
            "saida",
            "--backend",
            "glpi",
            "--url",
            f"http://127.0.0.1:{porta}",
            "--app-token",
            "app",
            "--user-token",
            "user",
        ]) == 0
        assert "99" in capsys.readouterr().out
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_cli_validar_exemplos(capsys):
    assert main(["validar", str(EXEMPLOS / "chamado_bom.json")]) == 0
    assert "Nota: 100/100" in capsys.readouterr().out

    assert main(["validar", str(EXEMPLOS / "chamado_ruim.json"), "--estrito"]) == 1
    saida = capsys.readouterr().out
    assert "REPROVADO" in saida and "Pergunte" in saida


def test_cli_resumo_gera_texto_final(capsys):
    json_path = EXEMPLOS / "chamado_bom.json"
    assert main(["resumo", str(json_path)]) == 0
    saida = capsys.readouterr().out
    assert "Título:" in saida and "Solução aplicada" in saida


def test_cli_extrair_e_arquivo_inexistente(capsys, tmp_path):
    assert main(["extrair", str(EXEMPLOS / "conversa_exemplo.txt")]) == 0
    assert "11.222.333/0001-81" in capsys.readouterr().out
    assert main(["validar", str(tmp_path / "nao-existe.json")]) == 2
