from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from ..ml import DadosPaciente, LeituraSensor, ParametrosOperacionais, analisar
from .util import corpo_json
from ..services.auth import exigir_dispositivo, exigir_login, paciente_permitido
from ..services.pipeline import montar_dados, processar_leitura

bp = Blueprint("clinico", __name__, url_prefix="/api")


def _store():
    return current_app.extensions["store"]


@bp.post("/sinais")
@exigir_dispositivo
def receber_sinais():
    leitura = LeituraSensor.model_validate(corpo_json())
    return jsonify(processar_leitura(_store(), leitura)), 201


@bp.get("/sinais/ultimo")
@exigir_login()
def ultimo_sinal():
    paciente_id = paciente_permitido(request.args.get("paciente_id"))
    if paciente_id is None:
        return jsonify({"erro": "acesso_negado"}), 403
    leitura = _store().ultima_leitura(paciente_id)
    if leitura is None:
        return jsonify({"erro": "sem_leituras", "paciente_id": paciente_id}), 404
    return jsonify(leitura)


@bp.get("/sinais/historico")
@exigir_login()
def historico():
    paciente_id = paciente_permitido(request.args.get("paciente_id"))
    if paciente_id is None:
        return jsonify({"erro": "acesso_negado"}), 403
    limite = min(max(request.args.get("limite", default=50, type=int), 1), 500)
    return jsonify({"paciente_id": paciente_id, "leituras": _store().historico(paciente_id, limite)})


@bp.post("/risco")
@exigir_login()
def risco():
    dados = DadosPaciente.model_validate(corpo_json())
    return jsonify(analisar(current_app.config["MODEL_PATH"], dados))


@bp.post("/analise")
@exigir_login()
def analise():
    corpo = corpo_json()
    paciente_id = paciente_permitido(corpo.get("paciente_id"))
    if paciente_id is None:
        return jsonify({"erro": "acesso_negado"}), 403
    ultima = _store().ultima_leitura(paciente_id)
    if ultima is None:
        return jsonify({"erro": "sem_leituras", "paciente_id": paciente_id}), 404
    sinais = ultima["sinais"]
    dados = montar_dados(
        _store(),
        paciente_id,
        sinais["fc_media"],
        sinais["temperatura"],
        sinais["spo2_media"],
        sinais["pa_sistolica"],
    )
    resultado = analisar(current_app.config["MODEL_PATH"], dados)
    return jsonify({"paciente_id": paciente_id, "entrada": dados.model_dump(), **resultado})


@bp.get("/pacientes")
@exigir_login("medico")
def pacientes():
    itens = []
    for paciente in _store().listar_pacientes():
        ultima = _store().ultima_leitura(paciente["id"])
        itens.append(
            {
                **paciente,
                "ultima_classificacao": ultima["classificacao"] if ultima else None,
                "ultima_probabilidade": ultima["probabilidade_crise"] if ultima else None,
                "ultima_atualizacao": ultima["timestamp"] if ultima else None,
            }
        )
    return jsonify({"pacientes": itens, "solicitante": g.identidade["usuario"]})


@bp.get("/operacao")
@exigir_login("medico")
def ler_operacao():
    return jsonify(_store().operacao())


@bp.put("/operacao")
@exigir_login("medico")
def atualizar_operacao():
    parametros = ParametrosOperacionais.model_validate(corpo_json())
    valores = {k: v for k, v in parametros.model_dump().items() if v is not None}
    return jsonify(_store().atualizar_operacao(valores))
