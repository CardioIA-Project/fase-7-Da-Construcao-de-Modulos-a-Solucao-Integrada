from __future__ import annotations

import json

from flask import Flask, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from .config import Config
from .ml.modelo import carregar
from .routes import auth, chat, clinico
from .services.pipeline import popular_demo
from .services.store import Store
from .services.triagem import TriagemService
from .services.triagem_hibrida import TriagemHibrida
from .services.watson import criar_cliente


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    if config:
        app.config.update(config)

    origens = app.config["CORS_ORIGINS"]
    CORS(app, origins="*" if origens == "*" else [o.strip() for o in origens.split(",")])

    app.extensions["store"] = Store(app.config["DB_PATH"], app.config["OPERACAO_PADRAO"])
    cliente_watson = app.config.get("WATSON_CLIENT")
    if cliente_watson is None:
        try:
            cliente_watson = criar_cliente(app.config)
        except Exception:
            app.logger.exception("Watson não pôde ser iniciado, usando triagem local")
            cliente_watson = None
    app.extensions["triagem"] = TriagemHibrida(TriagemService(), cliente_watson)

    with app.app_context():
        carregar(app.config["MODEL_PATH"])
        if app.config["SEED_DEMO"]:
            popular_demo(app.extensions["store"])

    app.register_blueprint(auth.bp)
    app.register_blueprint(clinico.bp)
    app.register_blueprint(chat.bp)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(ValidationError)
    def erro_validacao(erro: ValidationError):
        detalhes = json.loads(erro.json(include_url=False, include_context=False, include_input=False))
        return jsonify({"erro": "validacao", "detalhes": detalhes}), 422

    nomes_http = {
        400: "requisicao_invalida",
        404: "rota_nao_encontrada",
        405: "metodo_nao_permitido",
        413: "corpo_muito_grande",
    }

    @app.errorhandler(HTTPException)
    def erro_http(erro: HTTPException):
        corpo = {"erro": nomes_http.get(erro.code, erro.name.lower().replace(" ", "_"))}
        if erro.code == 400 and erro.description:
            corpo["detalhe"] = erro.description
        return jsonify(corpo), erro.code

    @app.errorhandler(Exception)
    def erro_interno(erro: Exception):
        app.logger.exception("erro interno")
        return jsonify({"erro": "erro_interno"}), 500

    return app
