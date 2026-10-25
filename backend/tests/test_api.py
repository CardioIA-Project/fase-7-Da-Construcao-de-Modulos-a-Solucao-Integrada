def test_health(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.get_json() == {"status": "ok"}


def test_login_valido_e_invalido(client):
    ok = client.post("/api/auth/login", json={"usuario": "medico", "senha": "medico123"})
    assert ok.status_code == 200
    assert ok.get_json()["perfil"] == "medico"
    assert "token" in ok.get_json()
    ruim = client.post("/api/auth/login", json={"usuario": "medico", "senha": "errada"})
    assert ruim.status_code == 401


def test_rotas_protegidas_exigem_token(client):
    assert client.get("/api/sinais/ultimo").status_code == 401
    assert client.get("/api/pacientes").status_code == 401


def test_sinais_exigem_chave_do_dispositivo(client):
    corpo = {"paciente_id": "p001", "fc_media": 80, "temperatura": 24}
    assert client.post("/api/sinais", json=corpo).status_code == 401
    assert client.post("/api/sinais", json=corpo, headers={"X-Device-Key": "x"}).status_code == 401


def test_leitura_critica_gera_risco_alto(client, cabecalho_dispositivo, cabecalho_medico):
    corpo = {"paciente_id": "p001", "fc_media": 130, "temperatura": 24, "spo2_media": 85}
    resposta = client.post("/api/sinais", json=corpo, headers=cabecalho_dispositivo)
    assert resposta.status_code == 201
    dados = resposta.get_json()
    assert dados["classificacao"] == "ALTO"
    ids = {p["id"] for p in dados["protocolos"]}
    assert {"spo2_critica", "fc_alta", "risco_sistemico_alto"} <= ids
    ultimo = client.get("/api/sinais/ultimo?paciente_id=p001", headers=cabecalho_medico)
    assert ultimo.status_code == 200
    assert ultimo.get_json()["classificacao"] == "ALTO"


def test_leitura_normal_gera_risco_baixo(client, cabecalho_dispositivo):
    corpo = {"paciente_id": "p001", "fc_media": 72, "temperatura": 24, "spo2_media": 97}
    dados = client.post("/api/sinais", json=corpo, headers=cabecalho_dispositivo).get_json()
    assert dados["classificacao"] == "BAIXO"
    assert dados["protocolos"] == []


def test_valores_fora_da_faixa_retornam_422(client, cabecalho_dispositivo):
    corpo = {"paciente_id": "p001", "fc_media": 400, "temperatura": 24}
    resposta = client.post("/api/sinais", json=corpo, headers=cabecalho_dispositivo)
    assert resposta.status_code == 422
    assert resposta.get_json()["erro"] == "validacao"


def test_campo_extra_e_rejeitado(client, cabecalho_dispositivo):
    corpo = {"paciente_id": "p001", "fc_media": 80, "temperatura": 24, "foo": 1}
    assert client.post("/api/sinais", json=corpo, headers=cabecalho_dispositivo).status_code == 422


def test_paciente_nao_acessa_outro_paciente(client, cabecalho_dispositivo, cabecalho_paciente):
    client.post(
        "/api/sinais",
        json={"paciente_id": "p002", "fc_media": 80, "temperatura": 24},
        headers=cabecalho_dispositivo,
    )
    assert client.get("/api/sinais/ultimo?paciente_id=p002", headers=cabecalho_paciente).status_code == 403
    assert client.get("/api/pacientes", headers=cabecalho_paciente).status_code == 403


def test_paciente_ve_os_proprios_dados_sem_informar_id(client, cabecalho_dispositivo, cabecalho_paciente):
    client.post(
        "/api/sinais",
        json={"paciente_id": "p001", "fc_media": 80, "temperatura": 24},
        headers=cabecalho_dispositivo,
    )
    resposta = client.get("/api/sinais/ultimo", headers=cabecalho_paciente)
    assert resposta.status_code == 200
    assert resposta.get_json()["paciente_id"] == "p001"


def test_historico_retorna_em_ordem_cronologica(client, cabecalho_dispositivo, cabecalho_medico):
    for fc in (70, 75, 80):
        client.post(
            "/api/sinais",
            json={"paciente_id": "p001", "fc_media": fc, "temperatura": 24},
            headers=cabecalho_dispositivo,
        )
    resposta = client.get("/api/sinais/historico?paciente_id=p001", headers=cabecalho_medico)
    fcs = [l["sinais"]["fc_media"] for l in resposta.get_json()["leituras"]]
    assert fcs == [70, 75, 80]


def test_eventos_contam_episodios_e_nao_leituras(client, cabecalho_dispositivo, app):
    critico = {"paciente_id": "p001", "fc_media": 130, "temperatura": 24, "spo2_media": 85}
    normal = {"paciente_id": "p001", "fc_media": 72, "temperatura": 24, "spo2_media": 97}
    for corpo in (critico, critico, critico, normal, critico):
        client.post("/api/sinais", json=corpo, headers=cabecalho_dispositivo)
    assert app.extensions["store"].eventos_24h("p001") == 2


def test_risco_com_payload_completo(client, cabecalho_medico):
    corpo = {
        "idade_media": 60,
        "carga_sistema": 90,
        "tempo_espera": 70,
        "fc_media": 100,
        "spo2_media": 95,
        "pa_sistolica": 120,
        "temperatura": 24,
        "densidade_eventos": 3,
        "eventos_24h": 1,
        "disponibilidade_recursos": 60,
    }
    resposta = client.post("/api/risco", json=corpo, headers=cabecalho_medico)
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["classificacao"] == "ALTO"
    assert "Carga do sistema acima de 80%" in dados["fatores"]
    assert "Tempo de espera acima de 60 min" in dados["fatores"]


def test_risco_rejeita_campo_extra(client, cabecalho_medico):
    resposta = client.post("/api/risco", json={"foo": 1}, headers=cabecalho_medico)
    assert resposta.status_code == 422


def test_analise_usa_ultima_leitura(client, cabecalho_dispositivo, cabecalho_medico):
    client.post(
        "/api/sinais",
        json={"paciente_id": "p001", "fc_media": 130, "temperatura": 24, "spo2_media": 85},
        headers=cabecalho_dispositivo,
    )
    resposta = client.post("/api/analise", json={"paciente_id": "p001"}, headers=cabecalho_medico)
    assert resposta.status_code == 200
    assert resposta.get_json()["classificacao"] == "ALTO"


def test_analise_sem_leituras_retorna_404(client, cabecalho_medico):
    resposta = client.post("/api/analise", json={"paciente_id": "p001"}, headers=cabecalho_medico)
    assert resposta.status_code == 404


def test_operacao_so_medico_altera_e_afeta_risco(client, cabecalho_dispositivo, cabecalho_medico, cabecalho_paciente):
    assert client.put("/api/operacao", json={"carga_sistema": 95}, headers=cabecalho_paciente).status_code == 403
    atualizado = client.put(
        "/api/operacao",
        json={"carga_sistema": 95, "tempo_espera": 80},
        headers=cabecalho_medico,
    )
    assert atualizado.status_code == 200
    assert atualizado.get_json()["carga_sistema"] == 95
    corpo = {"paciente_id": "p001", "fc_media": 72, "temperatura": 24, "spo2_media": 97}
    dados = client.post("/api/sinais", json=corpo, headers=cabecalho_dispositivo).get_json()
    assert dados["classificacao"] == "ALTO"


def test_lista_de_pacientes_para_medico(client, cabecalho_dispositivo, cabecalho_medico):
    client.post(
        "/api/sinais",
        json={"paciente_id": "p001", "fc_media": 72, "temperatura": 24},
        headers=cabecalho_dispositivo,
    )
    resposta = client.get("/api/pacientes", headers=cabecalho_medico)
    assert resposta.status_code == 200
    ids = [p["id"] for p in resposta.get_json()["pacientes"]]
    assert "p001" in ids
