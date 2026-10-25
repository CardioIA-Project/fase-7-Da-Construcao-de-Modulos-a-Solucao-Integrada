from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from .util import corpo_json
from ..services.auth import autenticar, exigir_login, gerar_token

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    corpo = corpo_json()
    usuario = str(corpo.get("usuario", "")).strip()
    senha = str(corpo.get("senha", ""))
    identidade = autenticar(usuario, senha)
    if identidade is None:
        return jsonify({"erro": "credenciais_invalidas"}), 401
    return jsonify({"token": gerar_token(identidade), **identidade})


@bp.get("/me")
@exigir_login()
def me():
    return jsonify(g.identidade)
