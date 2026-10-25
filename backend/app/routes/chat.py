from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from .util import corpo_json

bp = Blueprint("chat", __name__, url_prefix="/api")


def _triagem():
    return current_app.extensions["triagem"]


@bp.post("/session")
def criar_sessao():
    return jsonify({"session_id": _triagem().criar_sessao()}), 201


@bp.post("/message")
def enviar_mensagem():
    corpo = corpo_json()
    sessao_id = str(corpo.get("session_id", ""))
    texto = corpo.get("text")
    if not sessao_id or not isinstance(texto, str):
        return jsonify({"erro": "session_id e text sao obrigatorios"}), 400
    resposta = _triagem().responder(sessao_id, texto)
    if resposta is None:
        return jsonify({"erro": "sessao_nao_encontrada"}), 404
    return jsonify(resposta)


@bp.delete("/session/<sessao_id>")
def encerrar_sessao(sessao_id: str):
    if not _triagem().encerrar_sessao(sessao_id):
        return jsonify({"erro": "sessao_nao_encontrada"}), 404
    return jsonify({"status": "session encerrada"})
