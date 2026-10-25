from __future__ import annotations

from flask import request
from werkzeug.exceptions import BadRequest


def corpo_json() -> dict:
    corpo = request.get_json(silent=True)
    if corpo is None:
        return {}
    if not isinstance(corpo, dict):
        raise BadRequest("O corpo da requisição deve ser um objeto JSON.")
    return corpo
