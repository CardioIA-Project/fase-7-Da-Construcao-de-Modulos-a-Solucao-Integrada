from __future__ import annotations

import hmac
from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SAL = "cardioia-auth"


def _serializador() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SAL)


def autenticar(usuario: str, senha: str) -> dict | None:
    cadastro = current_app.config["USUARIOS"].get(usuario)
    if not cadastro:
        return None
    if not hmac.compare_digest(cadastro["senha"].encode(), senha.encode()):
        return None
    return {
        "usuario": usuario,
        "perfil": cadastro["perfil"],
        "nome": cadastro["nome"],
        "paciente_id": cadastro["paciente_id"],
    }


def gerar_token(identidade: dict) -> str:
    return _serializador().dumps(identidade)


def _ler_token() -> dict | None:
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        return None
    try:
        return _serializador().loads(
            cabecalho[7:].strip(), max_age=current_app.config["TOKEN_MAX_AGE"]
        )
    except (BadSignature, SignatureExpired):
        return None


def exigir_login(*perfis: str):
    def decorador(funcao):
        @wraps(funcao)
        def interno(*args, **kwargs):
            identidade = _ler_token()
            if identidade is None:
                return jsonify({"erro": "nao_autenticado"}), 401
            if perfis and identidade["perfil"] not in perfis:
                return jsonify({"erro": "acesso_negado"}), 403
            g.identidade = identidade
            return funcao(*args, **kwargs)

        return interno

    return decorador


def exigir_dispositivo(funcao):
    @wraps(funcao)
    def interno(*args, **kwargs):
        chave = request.headers.get("X-Device-Key", "")
        esperada = current_app.config["DEVICE_API_KEY"]
        if not chave or not hmac.compare_digest(chave.encode(), esperada.encode()):
            return jsonify({"erro": "dispositivo_nao_autorizado"}), 401
        return funcao(*args, **kwargs)

    return interno


def paciente_permitido(paciente_id: str | None) -> str | None:
    identidade = g.identidade
    if identidade["perfil"] == "paciente":
        if paciente_id and paciente_id != identidade["paciente_id"]:
            return None
        return identidade["paciente_id"]
    return paciente_id or current_app.config["PACIENTE_PADRAO"]
