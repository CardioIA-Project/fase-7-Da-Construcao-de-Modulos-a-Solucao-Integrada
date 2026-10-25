import json

import pytest

from app.services import triagem as modulo_triagem
from app.services.triagem import TriagemService


@pytest.mark.parametrize("rota", ["/api/auth/login", "/api/message", "/api/analise", "/api/sinais", "/api/risco", "/api/operacao"])
@pytest.mark.parametrize("corpo", ["[1, 2]", '"texto"', "42"])
def test_corpo_que_nao_e_objeto_nunca_gera_500(client, cabecalho_medico, cabecalho_dispositivo, rota, corpo):
    cabecalhos = {**cabecalho_medico, **cabecalho_dispositivo}
    metodo = client.put if rota == "/api/operacao" else client.post
    resposta = metodo(rota, data=corpo, content_type="application/json", headers=cabecalhos)
    assert resposta.status_code in (400, 422)
    assert resposta.is_json


def test_json_quebrado_nao_gera_500(client, cabecalho_dispositivo):
    resposta = client.post("/api/sinais", data="{", content_type="application/json", headers=cabecalho_dispositivo)
    assert resposta.status_code in (400, 422)
    assert resposta.is_json


def test_corpo_gigante_e_recusado(client, cabecalho_dispositivo):
    resposta = client.post(
        "/api/sinais",
        data="x" * (70 * 1024),
        content_type="application/json",
        headers=cabecalho_dispositivo,
    )
    assert resposta.status_code == 413
    assert resposta.get_json() == {"erro": "corpo_muito_grande"}


def test_infinito_em_operacao_e_recusado_e_nao_envenena_leituras(client, cabecalho_medico, cabecalho_dispositivo):
    resposta = client.put(
        "/api/operacao", data='{"tempo_espera": 1e999}', content_type="application/json", headers=cabecalho_medico
    )
    assert resposta.status_code == 422
    assert client.get("/api/operacao", headers=cabecalho_medico).get_json()["tempo_espera"] == 30
    ok = client.post(
        "/api/sinais",
        json={"paciente_id": "p001", "fc_media": 80, "temperatura": 24},
        headers=cabecalho_dispositivo,
    )
    assert ok.status_code == 201


def test_valor_gigante_em_operacao_e_recusado(client, cabecalho_medico):
    assert client.put("/api/operacao", json={"tempo_espera": 1e12}, headers=cabecalho_medico).status_code == 422
    assert client.put("/api/operacao", json={"carga_sistema": 101}, headers=cabecalho_medico).status_code == 422


def test_infinito_em_risco_retorna_422(client, cabecalho_medico):
    corpo = (
        '{"idade_media":50,"carga_sistema":50,"tempo_espera":1e999,"fc_media":80,"spo2_media":96,'
        '"pa_sistolica":120,"temperatura":24,"densidade_eventos":3,"eventos_24h":1,"disponibilidade_recursos":60}'
    )
    resposta = client.post("/api/risco", data=corpo, content_type="application/json", headers=cabecalho_medico)
    assert resposta.status_code == 422


@pytest.mark.parametrize("identificador", ["   ", "", "a b", "p001; DROP TABLE", "x" * 41, "pacíente"])
def test_paciente_id_invalido_e_recusado(client, cabecalho_dispositivo, identificador):
    corpo = {"paciente_id": identificador, "fc_media": 80, "temperatura": 24}
    assert client.post("/api/sinais", json=corpo, headers=cabecalho_dispositivo).status_code == 422


def test_paciente_id_com_espacos_nas_pontas_e_normalizado(client, cabecalho_dispositivo):
    corpo = {"paciente_id": " p009 ", "fc_media": 80, "temperatura": 24}
    resposta = client.post("/api/sinais", json=corpo, headers=cabecalho_dispositivo)
    assert resposta.status_code == 201
    assert resposta.get_json()["paciente_id"] == "p009"


def test_token_adulterado_e_expirado(client, app, cabecalho_medico):
    token = cabecalho_medico["Authorization"]
    assert client.get("/api/auth/me", headers=cabecalho_medico).status_code == 200
    assert client.get("/api/auth/me", headers={"Authorization": token[:-3] + "abc"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Basic xyz"}).status_code == 401
    app.config["TOKEN_MAX_AGE"] = -1
    assert client.get("/api/auth/me", headers=cabecalho_medico).status_code == 401


def test_cors_preflight_libera_authorization_e_chave_do_dispositivo(client):
    resposta = client.options(
        "/api/sinais",
        headers={
            "Origin": "https://cardioia.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-device-key,authorization",
        },
    )
    assert resposta.status_code == 200
    assert resposta.headers["Access-Control-Allow-Origin"] == "https://cardioia.vercel.app"
    permitidos = resposta.headers["Access-Control-Allow-Headers"].lower()
    assert "authorization" in permitidos and "x-device-key" in permitidos


def test_rota_inexistente_e_metodo_errado_retornam_json(client):
    assert client.get("/nao-existe").get_json() == {"erro": "rota_nao_encontrada"}
    assert client.delete("/health").get_json() == {"erro": "metodo_nao_permitido"}


def test_erro_inesperado_vira_json_500(app, client, monkeypatch):
    def quebrar(*_):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr("app.routes.clinico.analisar", quebrar)
    token = client.post("/api/auth/login", json={"usuario": "medico", "senha": "medico123"}).get_json()["token"]
    corpo = {
        "idade_media": 50, "carga_sistema": 50, "tempo_espera": 30, "fc_media": 80, "spo2_media": 96,
        "pa_sistolica": 120, "temperatura": 24, "densidade_eventos": 3, "eventos_24h": 1,
        "disponibilidade_recursos": 60,
    }
    resposta = client.post("/api/risco", json=corpo, headers={"Authorization": "Bearer " + token})
    assert resposta.status_code == 500
    assert resposta.get_json() == {"erro": "erro_interno"}


def _emergencia(client, texto):
    sessao = client.post("/api/session").get_json()["session_id"]
    return client.post("/api/message", json={"session_id": sessao, "text": texto}).get_json()["emergencia"]


@pytest.mark.parametrize(
    "texto",
    [
        "cansaço e dor no braço",
        "palpitação e suor frio",
        "formigamento no braço esquerdo e cansaço",
        "tontura e falta de ar",
        "estou cansado e com dor no peito",
        "coração disparado e dor no peito",
        "sinto o peito doendo",
        "sinto um aperto no tórax",
        "dor forte no peito esquerdo",
        "não consigo respirar direito",
        "meu braço esquerdo está dormente",
        "estou suando frio",
        "DOR NO PEITO!!!",
        "dor  no  peito",
        "sem ar",
        "pressão no peito",
    ],
)
def test_emergencia_tem_prioridade_sobre_sintomas_leves(client, texto):
    assert _emergencia(client, texto) is True


@pytest.mark.parametrize(
    "texto",
    [
        "sempre sinto palpitação ao andar",
        "sempre fico cansado ao andar de ar condicionado",
        "tenho tontura de manhã",
        "minhas pernas estão inchadas",
        "coração disparado e tontura",
        "estou com cansaço",
    ],
)
def test_sintomas_leves_nao_disparam_emergencia(client, texto):
    assert _emergencia(client, texto) is False


def test_sessoes_expiram(monkeypatch):
    servico = TriagemService()
    sessao = servico.criar_sessao()
    assert servico.responder(sessao, "oi") is not None
    base = modulo_triagem.time.monotonic()
    monkeypatch.setattr(modulo_triagem.time, "monotonic", lambda: base + modulo_triagem.TTL_SESSAO_S + 5)
    assert servico.responder(sessao, "oi") is None
    assert servico.existe(sessao) is False


def test_limite_de_sessoes_descarta_as_mais_antigas(monkeypatch):
    monkeypatch.setattr(modulo_triagem, "MAX_SESSOES", 5)
    servico = TriagemService()
    ids = [servico.criar_sessao() for _ in range(12)]
    assert len(servico._sessoes) <= 5
    assert servico.existe(ids[-1])
    assert not servico.existe(ids[0])


def test_resposta_do_chat_e_serializavel(client):
    sessao = client.post("/api/session").get_json()["session_id"]
    resposta = client.post("/api/message", json={"session_id": sessao, "text": "oi"})
    json.loads(resposta.get_data(as_text=True))


def test_arquivo_env_e_lido_e_nao_sobrescreve_ambiente(tmp_path, monkeypatch):
    from app import config as modulo_config

    arquivo = tmp_path / ".env"
    arquivo.write_text('# comentario\nVAR_TESTE_A=um\nVAR_TESTE_B="dois"\nVAR_TESTE_C=\nsem_igual\n', encoding="utf-8")
    monkeypatch.delenv("CARDIOIA_IGNORAR_ENV", raising=False)
    monkeypatch.delenv("VAR_TESTE_A", raising=False)
    monkeypatch.delenv("VAR_TESTE_B", raising=False)
    monkeypatch.delenv("VAR_TESTE_C", raising=False)
    monkeypatch.setenv("VAR_TESTE_C", "do-ambiente")
    modulo_config._carregar_env(arquivo)
    import os

    assert os.environ["VAR_TESTE_A"] == "um"
    assert os.environ["VAR_TESTE_B"] == "dois"
    assert os.environ["VAR_TESTE_C"] == "do-ambiente"
    monkeypatch.delenv("VAR_TESTE_A")
    monkeypatch.delenv("VAR_TESTE_B")
