import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.services.watson import WatsonClient, criar_cliente

RESPOSTA = {
    "output": {
        "generic": [
            {"response_type": "text", "text": "Bem-vindo, como posso ajudá-lo?"},
            {
                "response_type": "option",
                "options": [
                    {"label": "Dor no peito", "value": {"input": {"text": "Dor no peito"}}},
                    {"label": "Tontura ", "value": {"input": {"text": "Tontura "}}},
                ],
            },
        ]
    }
}


class Servidor:
    def __init__(self, atraso=0.0, expirar_primeiro_token=False, status_erro=None):
        self.requisicoes = []
        self.chamadas_iam = 0
        estado = self
        self._expirar = expirar_primeiro_token
        self._status_erro = status_erro

        class Handler(BaseHTTPRequestHandler):
            def _corpo(self):
                tamanho = int(self.headers.get("Content-Length") or 0)
                return self.rfile.read(tamanho)

            def _responder(self, codigo, corpo=None):
                time.sleep(atraso)
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json")
                dados = json.dumps(corpo).encode() if corpo is not None else b""
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                try:
                    self.wfile.write(dados)
                except OSError:
                    pass

            def _api(self, metodo):
                bruto = self._corpo()
                autorizacao = self.headers.get("Authorization", "")
                estado.requisicoes.append((metodo, self.path, json.loads(bruto) if bruto else None, autorizacao))
                if estado._status_erro:
                    return self._responder(estado._status_erro, {"error": "falha"})
                if estado._expirar and autorizacao == "Bearer token-1":
                    return self._responder(401, {"error": "expirado"})
                if metodo == "DELETE":
                    return self._responder(204)
                if self.path.split("?")[0].endswith("/message"):
                    return self._responder(200, RESPOSTA)
                return self._responder(201, {"session_id": "S1"})

            def do_POST(self):
                if self.path == "/identity/token":
                    self._corpo()
                    estado.chamadas_iam += 1
                    return self._responder(200, {"access_token": f"token-{estado.chamadas_iam}", "expires_in": 3600})
                self._api("POST")

            def do_DELETE(self):
                self._api("DELETE")

            def log_message(self, *args):
                pass

        self.http = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.http.server_port}"
        self.iam = self.url + "/identity/token"
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def parar(self):
        self.http.shutdown()
        self.http.server_close()


@pytest.fixture()
def servidor():
    s = Servidor()
    yield s
    s.parar()


def _cliente(servidor, **extra):
    return WatsonClient("chave", servidor.url, "ASSISTENTE", "2021-06-14", 5, iam_url=servidor.iam, **extra)


def test_ciclo_completo_no_formato_antigo_da_fase_5(servidor):
    cliente = _cliente(servidor)
    sessao = cliente.criar_sessao()
    assert sessao == "S1"
    resposta = cliente.enviar(sessao, "oi")
    assert resposta == {"replies": ["Bem-vindo, como posso ajudá-lo?"], "options": ["Dor no peito", "Tontura"]}
    cliente.encerrar(sessao)
    chamadas = [(m, p.split("?")[0]) for m, p, _, _ in servidor.requisicoes]
    assert chamadas == [
        ("POST", "/v2/assistants/ASSISTENTE/sessions"),
        ("POST", "/v2/assistants/ASSISTENTE/sessions/S1/message"),
        ("DELETE", "/v2/assistants/ASSISTENTE/sessions/S1"),
    ]
    assert all("version=2021-06-14" in p for _, p, _, _ in servidor.requisicoes)
    assert servidor.requisicoes[1][2] == {"input": {"message_type": "text", "text": "oi"}}
    assert all(a == "Bearer token-1" for _, _, _, a in servidor.requisicoes)


def test_formato_novo_com_environment_id(servidor):
    cliente = _cliente(servidor, environment_id="AMBIENTE")
    sessao = cliente.criar_sessao()
    cliente.enviar(sessao, "oi")
    cliente.encerrar(sessao)
    chamadas = [(m, p.split("?")[0]) for m, p, _, _ in servidor.requisicoes]
    assert chamadas == [
        ("POST", "/v2/assistants/ASSISTENTE/environments/AMBIENTE/sessions"),
        ("POST", "/v2/assistants/ASSISTENTE/environments/AMBIENTE/sessions/S1/message"),
        ("DELETE", "/v2/assistants/ASSISTENTE/environments/AMBIENTE/sessions/S1"),
    ]


def test_token_e_reaproveitado_entre_chamadas(servidor):
    cliente = _cliente(servidor)
    cliente.criar_sessao()
    cliente.enviar("S1", "a")
    cliente.enviar("S1", "b")
    assert servidor.chamadas_iam == 1


def test_token_expirado_renova_e_repete_uma_vez():
    s = Servidor(expirar_primeiro_token=True)
    try:
        cliente = _cliente(s)
        assert cliente.criar_sessao() == "S1"
        assert s.chamadas_iam == 2
        assert [a for _, _, _, a in s.requisicoes] == ["Bearer token-1", "Bearer token-2"]
    finally:
        s.parar()


def test_url_com_barra_final_e_aceita(servidor):
    cliente = WatsonClient("chave", servidor.url + "/", "A", "2021-06-14", 5, iam_url=servidor.iam)
    assert cliente.criar_sessao() == "S1"
    assert servidor.requisicoes[0][1].startswith("/v2/assistants/A/sessions")


@pytest.mark.parametrize("status", [400, 403, 404, 500, 503])
def test_erro_http_vira_excecao(status):
    s = Servidor(status_erro=status)
    try:
        with pytest.raises(Exception):
            _cliente(s).criar_sessao()
    finally:
        s.parar()


def test_timeout_e_respeitado():
    lento = Servidor(atraso=2.0)
    try:
        cliente = WatsonClient("chave", lento.url, "A", "2021-06-14", 0.3, iam_url=lento.iam)
        inicio = time.monotonic()
        with pytest.raises(Exception):
            cliente.criar_sessao()
        assert time.monotonic() - inicio < 1.5
    finally:
        lento.parar()


def test_iam_fora_do_ar_vira_excecao():
    cliente = WatsonClient("chave", "http://127.0.0.1:9", "A", "2021-06-14", 1, iam_url="http://127.0.0.1:9/identity/token")
    with pytest.raises(Exception):
        cliente.criar_sessao()


def test_criar_cliente_exige_as_tres_variaveis():
    base = {"WATSON_API_KEY": "k", "WATSON_URL": "http://x", "WATSON_ASSISTANT_ID": "a", "WATSON_VERSION": "2021-06-14", "WATSON_TIMEOUT": 6}
    assert criar_cliente({**base, "WATSON_API_KEY": ""}) is None
    assert criar_cliente({**base, "WATSON_URL": " "}) is None
    assert criar_cliente({**base, "WATSON_ASSISTANT_ID": ""}) is None
    cliente = criar_cliente({**base, "WATSON_ENVIRONMENT_ID": " E1 "})
    assert cliente is not None
    assert "/environments/E1" in cliente._base()
    assert "/environments" not in criar_cliente(base)._base()


def test_script_de_diagnostico_com_servidor_falso(servidor, capsys):
    import testar_watson

    config = {
        "WATSON_API_KEY": "chave-secreta-123",
        "WATSON_URL": servidor.url,
        "WATSON_ASSISTANT_ID": "ASSISTENTE",
        "WATSON_VERSION": "2021-06-14",
        "WATSON_TIMEOUT": 5,
        "WATSON_IAM_URL": servidor.iam,
    }
    assert testar_watson.main(config) == 0
    saida = capsys.readouterr().out
    assert "Tudo certo" in saida
    assert "chave-secreta-123" not in saida


def test_script_de_diagnostico_mostra_dica_em_erro_http(capsys):
    import testar_watson

    s = Servidor(status_erro=404)
    try:
        config = {
            "WATSON_API_KEY": "k",
            "WATSON_URL": s.url,
            "WATSON_ASSISTANT_ID": "X",
            "WATSON_VERSION": "2021-06-14",
            "WATSON_TIMEOUT": 5,
            "WATSON_IAM_URL": s.iam,
        }
        assert testar_watson.main(config) == 1
        saida = capsys.readouterr().out
        assert "status HTTP: 404" in saida
        assert "WATSON_ENVIRONMENT_ID" in saida
    finally:
        s.parar()


def test_script_de_diagnostico_sem_variaveis(capsys):
    import testar_watson

    assert testar_watson.main({"WATSON_API_KEY": "", "WATSON_URL": "", "WATSON_ASSISTANT_ID": ""}) == 1
    assert "Faltam variáveis" in capsys.readouterr().out


def test_app_completo_com_cliente_real_contra_servidor_falso(servidor, tmp_path, caminho_modelo):
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "DB_PATH": str(tmp_path / "i.db"),
            "MODEL_PATH": caminho_modelo,
            "SEED_DEMO": False,
            "WATSON_API_KEY": "k",
            "WATSON_URL": servidor.url,
            "WATSON_ASSISTANT_ID": "ASSISTENTE",
            "WATSON_VERSION": "2021-06-14",
            "WATSON_TIMEOUT": 5,
            "WATSON_IAM_URL": servidor.iam,
        }
    )
    c = app.test_client()
    assert c.get("/api/triagem/status").get_json()["watson_configurado"] is True
    sessao = c.post("/api/session").get_json()["session_id"]
    resposta = c.post("/api/message", json={"session_id": sessao, "text": "oi"}).get_json()
    assert resposta["origem"] == "watson"
    assert resposta["options"] == ["Dor no peito", "Tontura"]
    emergencia = c.post("/api/message", json={"session_id": sessao, "text": "dor no peito"}).get_json()
    assert emergencia["origem"] == "local" and emergencia["emergencia"] is True
    assert c.delete(f"/api/session/{sessao}").status_code == 200
    assert servidor.requisicoes[-1][0] == "DELETE"


def test_app_com_watson_fora_do_ar_responde_pela_reserva(tmp_path, caminho_modelo):
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "DB_PATH": str(tmp_path / "j.db"),
            "MODEL_PATH": caminho_modelo,
            "SEED_DEMO": False,
            "WATSON_API_KEY": "k",
            "WATSON_URL": "http://127.0.0.1:9",
            "WATSON_ASSISTANT_ID": "A",
            "WATSON_VERSION": "2021-06-14",
            "WATSON_TIMEOUT": 1,
            "WATSON_IAM_URL": "http://127.0.0.1:9/identity/token",
        }
    )
    c = app.test_client()
    sessao = c.post("/api/session").get_json()["session_id"]
    resposta = c.post("/api/message", json={"session_id": sessao, "text": "Tontura"}).get_json()
    assert resposta["origem"] == "local"
    assert resposta["options"] == ["Leve", "Moderada", "Intensa"]
