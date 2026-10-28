import pytest

from app import create_app
from app.services import triagem_hibrida as modulo
from app.services.watson import extrair_resposta


class WatsonFalso:
    def __init__(self):
        self.criadas = []
        self.mensagens = []
        self.encerradas = []
        self.falha_criar = False
        self.falha_enviar = False
        self.falha_encerrar = False
        self.respostas = []

    def criar_sessao(self):
        if self.falha_criar:
            raise RuntimeError("watson fora do ar")
        self.criadas.append("w1")
        return "w1"

    def enviar(self, sessao, texto):
        self.mensagens.append((sessao, texto))
        if self.falha_enviar:
            raise TimeoutError("timeout")
        if self.respostas:
            return self.respostas.pop(0)
        return {"replies": ["Resposta do Watson"], "options": ["Leve", "Moderada", "Intensa"]}

    def encerrar(self, sessao):
        if self.falha_encerrar:
            raise RuntimeError("falha")
        self.encerradas.append(sessao)


@pytest.fixture()
def watson():
    return WatsonFalso()


@pytest.fixture()
def app_watson(tmp_path, caminho_modelo, watson):
    return create_app(
        {
            "TESTING": True,
            "DB_PATH": str(tmp_path / "w.db"),
            "MODEL_PATH": caminho_modelo,
            "SEED_DEMO": False,
            "WATSON_CLIENT": watson,
        }
    )


@pytest.fixture()
def c(app_watson):
    return app_watson.test_client()


def _abrir(c):
    return c.post("/api/session").get_json()["session_id"]


def _msg(c, sessao, texto):
    return c.post("/api/message", json={"session_id": sessao, "text": texto}).get_json()


def test_sem_watson_configurado_usa_local(client):
    sessao = _abrir(client)
    resposta = _msg(client, sessao, "oi")
    assert resposta["origem"] == "local"
    status = client.get("/api/triagem/status").get_json()
    assert status == {"watson_configurado": False, "watson_ativo": False, "reserva_local": True}


def test_resposta_vem_do_watson_quando_disponivel(c, watson):
    sessao = _abrir(c)
    resposta = _msg(c, sessao, "Tontura")
    assert resposta["origem"] == "watson"
    assert resposta["replies"] == ["Resposta do Watson"]
    assert resposta["options"] == ["Leve", "Moderada", "Intensa"]
    assert watson.mensagens == [("w1", "Tontura")]
    assert c.get("/api/triagem/status").get_json()["watson_ativo"] is True


def test_emergencia_e_decidida_localmente_sem_chamar_o_watson(c, watson):
    sessao = _abrir(c)
    resposta = _msg(c, sessao, "estou com dor no peito")
    assert resposta["emergencia"] is True
    assert resposta["finalizado"] is True
    assert resposta["origem"] == "local"
    assert "SAMU (192)" in resposta["replies"][0]
    assert watson.mensagens == []


def test_emergencia_funciona_mesmo_com_watson_fora_do_ar(c, watson):
    watson.falha_criar = True
    watson.falha_enviar = True
    sessao = _abrir(c)
    assert _msg(c, sessao, "dor no braço e cansaço")["emergencia"] is True


def test_falha_ao_enviar_cai_na_triagem_local(c, watson):
    sessao = _abrir(c)
    watson.falha_enviar = True
    resposta = _msg(c, sessao, "Tontura")
    assert resposta["origem"] == "local"
    assert resposta["options"] == ["Leve", "Moderada", "Intensa"]


def test_falha_ao_criar_sessao_nao_impede_a_conversa(c, watson):
    watson.falha_criar = True
    sessao = _abrir(c)
    resposta = _msg(c, sessao, "oi")
    assert resposta["origem"] == "local"
    assert watson.mensagens == []


def test_estado_local_acompanha_o_watson_para_a_reserva_funcionar_no_meio(c, watson):
    sessao = _abrir(c)
    assert _msg(c, sessao, "Tontura")["origem"] == "watson"
    watson.falha_enviar = True
    resposta = _msg(c, sessao, "Leve")
    assert resposta["origem"] == "local"
    assert resposta["options"] == ["Minutos", "Horas", "Dias", "Semanas"]


def test_circuito_abre_apos_falhas_e_fecha_depois_da_pausa(c, watson, monkeypatch):
    watson.falha_enviar = True
    sessao = _abrir(c)
    for _ in range(modulo.FALHAS_PARA_ABRIR):
        _msg(c, sessao, "oi")
    chamadas = len(watson.mensagens)
    assert c.get("/api/triagem/status").get_json()["watson_ativo"] is False
    _msg(c, sessao, "oi")
    assert len(watson.mensagens) == chamadas
    base = modulo.time.monotonic()
    monkeypatch.setattr(modulo.time, "monotonic", lambda: base + modulo.PAUSA_CIRCUITO_S + 1)
    watson.falha_enviar = False
    assert _msg(c, sessao, "oi")["origem"] == "watson"
    assert c.get("/api/triagem/status").get_json()["watson_ativo"] is True


def test_resumo_final_do_watson_marca_finalizado(c, watson):
    watson.respostas = [{"replies": ['Resumindo o que você me contou: sintoma Tontura.'], "options": []}]
    sessao = _abrir(c)
    resposta = _msg(c, sessao, "nenhum")
    assert resposta["finalizado"] is True
    assert resposta["emergencia"] is False


def test_resposta_vazia_do_watson_cai_na_local(c, watson):
    watson.respostas = [{"replies": [], "options": []}]
    sessao = _abrir(c)
    assert _msg(c, sessao, "oi")["origem"] == "local"


def test_encerrar_sessao_fecha_no_watson_e_ignora_falha(c, watson):
    sessao = _abrir(c)
    assert c.delete(f"/api/session/{sessao}").get_json() == {"status": "session encerrada"}
    assert watson.encerradas == ["w1"]
    watson.falha_encerrar = True
    outra = _abrir(c)
    assert c.delete(f"/api/session/{outra}").status_code == 200


def test_sessao_inexistente_continua_404(c):
    assert c.post("/api/message", json={"session_id": "nao-existe", "text": "oi"}).status_code == 404


def test_extrair_resposta_no_formato_real_do_watson():
    bruto = {
        "output": {
            "generic": [
                {"response_type": "text", "text": "Entendi. Esse assistente faz uma triagem inicial. Qual sintoma você está sentindo?"},
                {
                    "response_type": "option",
                    "title": "",
                    "options": [
                        {"label": "Dor no peito", "value": {"input": {"text": "Dor no peito"}}},
                        {"label": "Palpitação ", "value": {"input": {"text": "Palpitação "}}},
                        {"label": "", "value": {}},
                    ],
                },
                {"response_type": "image", "source": "x"},
                {"response_type": "text", "text": "   "},
            ]
        }
    }
    resultado = extrair_resposta(bruto)
    assert resultado["replies"] == ["Entendi. Esse assistente faz uma triagem inicial. Qual sintoma você está sentindo?"]
    assert resultado["options"] == ["Dor no peito", "Palpitação"]


def test_extrair_resposta_vazia():
    assert extrair_resposta({}) == {"replies": [], "options": []}
    assert extrair_resposta({"output": {"generic": []}}) == {"replies": [], "options": []}


def test_titulo_da_opcao_vira_texto():
    bruto = {"output": {"generic": [{"response_type": "option", "title": "Escolha:", "options": [{"label": "Leve"}]}]}}
    assert extrair_resposta(bruto) == {"replies": ["Escolha:"], "options": ["Leve"]}


def test_cliente_watson_invalido_nao_derruba_o_app(tmp_path, caminho_modelo, monkeypatch):
    def quebrar(_config):
        raise RuntimeError("sdk ausente")

    monkeypatch.setattr("app.criar_cliente", quebrar)
    app = create_app(
        {"TESTING": True, "DB_PATH": str(tmp_path / "x.db"), "MODEL_PATH": caminho_modelo, "SEED_DEMO": False}
    )
    c = app.test_client()
    sessao = c.post("/api/session").get_json()["session_id"]
    resposta = c.post("/api/message", json={"session_id": sessao, "text": "oi"}).get_json()
    assert resposta["origem"] == "local"


def test_oi_inicial_nao_entendido_pelo_watson_mostra_menu_local(c, watson):
    watson.respostas = [{"replies": ["Acho que não entendi. Reformule sua pergunta."], "options": []}]
    sessao = _abrir(c)
    corpo = _msg(c, sessao, "oi")
    assert corpo["origem"] == "local"
    assert corpo["replies"][0].startswith("Bem-vindo")
    assert "Tontura" in corpo["options"]
    seguinte = _msg(c, sessao, "Tontura")
    assert seguinte["origem"] == "watson"


def test_mensagem_vazia_abre_com_menu_local_sem_chamar_o_watson(c, watson):
    sessao = _abrir(c)
    corpo = _msg(c, sessao, "   ")
    assert corpo["origem"] == "local"
    assert corpo["options"]
    assert watson.mensagens == []


def test_nao_entendi_do_watson_no_meio_do_fluxo_mostra_opcoes_locais(c, watson):
    sessao = _abrir(c)
    _msg(c, sessao, "Tontura")
    watson.respostas = [{"replies": ["Acho que não entendi."], "options": []}]
    corpo = _msg(c, sessao, "talvez")
    assert corpo["origem"] == "local"
    assert corpo["options"] == ["Leve", "Moderada", "Intensa"]


def test_limpar_texto_corrige_o_resumo_real_do_watson():
    bruto = (
        '"Resumindo o que você me contou: você relatou o sintoma Tontura , '
        "classificado como Leve,há Horas. Isso não é um diagnóstico."
    )
    resposta = extrair_resposta({"output": {"generic": [{"response_type": "text", "text": bruto}]}})
    assert resposta["replies"] == [
        "Resumindo o que você me contou: você relatou o sintoma Tontura, "
        "classificado como Leve, há Horas. Isso não é um diagnóstico."
    ]


def test_limpar_texto_preserva_aspas_balanceadas_e_decimais():
    from app.services.watson import limpar_texto

    assert limpar_texto('Responda "nenhum", ou 1,5 vezes') == 'Responda "nenhum", ou 1,5 vezes'
    assert limpar_texto('"Oi"') == '"Oi"'
    assert limpar_texto("Texto normal.") == "Texto normal."
