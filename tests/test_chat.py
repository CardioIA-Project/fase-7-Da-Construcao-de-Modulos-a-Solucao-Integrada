def _abrir(client):
    return client.post("/api/session").get_json()["session_id"]


def _enviar(client, sessao, texto):
    return client.post("/api/message", json={"session_id": sessao, "text": texto})


def test_sintoma_critico_aciona_emergencia(client):
    sessao = _abrir(client)
    resposta = _enviar(client, sessao, "Estou sentindo dor no peito").get_json()
    assert resposta["emergencia"] is True
    assert resposta["finalizado"] is True
    assert "SAMU (192)" in resposta["replies"][0]


def test_cada_sintoma_critico_aciona_emergencia(client):
    for texto in ("Falta de ar", "Dor no braço", "Suor frio", "meu peito está apertado"):
        sessao = _abrir(client)
        assert _enviar(client, sessao, texto).get_json()["emergencia"] is True


def test_fluxo_completo_sintoma_leve(client):
    sessao = _abrir(client)
    primeira = _enviar(client, sessao, "oi").get_json()
    assert "Bem-vindo" in primeira["replies"][0]
    assert len(primeira["options"]) == 8
    severidade = _enviar(client, sessao, "Palpitação").get_json()
    assert severidade["options"] == ["Leve", "Moderada", "Intensa"]
    duracao = _enviar(client, sessao, "Leve").get_json()
    assert duracao["options"] == ["Minutos", "Horas", "Dias", "Semanas"]
    fatores = _enviar(client, sessao, "Horas").get_json()
    assert "fatores de risco" in fatores["replies"][0]
    final = _enviar(client, sessao, "tenho diabetes e sou fumante").get_json()
    texto = final["replies"][0]
    assert final["finalizado"] is True
    assert final["emergencia"] is False
    assert "Palpitação" in texto and "Leve" in texto and "horas" in texto
    assert "diabetes" in texto and "tabagismo" in texto
    assert "cardiologista" in texto


def test_sintoma_direto_na_primeira_mensagem(client):
    sessao = _abrir(client)
    resposta = _enviar(client, sessao, "sinto tontura").get_json()
    assert resposta["options"] == ["Leve", "Moderada", "Intensa"]


def test_nenhum_fator_de_risco(client):
    sessao = _abrir(client)
    for texto in ("Cansaço", "Moderada", "Dias"):
        _enviar(client, sessao, texto)
    final = _enviar(client, sessao, "nenhum").get_json()
    assert "não informou fatores" in final["replies"][0]


def test_opcao_numerica(client):
    sessao = _abrir(client)
    _enviar(client, sessao, "oi")
    resposta = _enviar(client, sessao, "4").get_json()
    assert resposta["options"] == ["Leve", "Moderada", "Intensa"]


def test_resposta_invalida_repete_e_depois_encerra(client):
    sessao = _abrir(client)
    _enviar(client, sessao, "Tontura")
    primeira = _enviar(client, sessao, "banana").get_json()
    assert "Eu não entendi" in primeira["replies"][0]
    assert primeira["options"] == ["Leve", "Moderada", "Intensa"]
    _enviar(client, sessao, "banana")
    ultima = _enviar(client, sessao, "banana").get_json()
    assert ultima["finalizado"] is True
    assert "procure um atendimento médico" in ultima["replies"][0]


def test_sessao_reinicia_apos_o_fim(client):
    sessao = _abrir(client)
    _enviar(client, sessao, "dor no peito")
    resposta = _enviar(client, sessao, "Tontura").get_json()
    assert resposta["options"] == ["Leve", "Moderada", "Intensa"]


def test_intensa_adiciona_alerta_no_resumo(client):
    sessao = _abrir(client)
    for texto in ("Tontura", "Intensa", "Horas"):
        _enviar(client, sessao, texto)
    final = _enviar(client, sessao, "nenhum").get_json()
    assert "não adie" in final["replies"][0]


def test_validacao_e_sessao_inexistente(client):
    assert client.post("/api/message", json={"text": "oi"}).status_code == 400
    assert _enviar(client, "inexistente", "oi").status_code == 404


def test_encerrar_sessao(client):
    sessao = _abrir(client)
    assert client.delete(f"/api/session/{sessao}").get_json() == {"status": "session encerrada"}
    assert client.delete(f"/api/session/{sessao}").status_code == 404
