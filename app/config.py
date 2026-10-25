from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _carregar_env(caminho: Path) -> None:
    if os.getenv("CARDIOIA_IGNORAR_ENV") or not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env(BASE_DIR / ".env")


def _bool(valor: str | None, padrao: bool) -> bool:
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-troque-em-producao")
    DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "cardioia-device-demo")
    DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "cardioia.db"))
    MODEL_PATH = os.getenv("MODEL_PATH", str(BASE_DIR / "modelo_risco_cardiaco.pkl"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    TOKEN_MAX_AGE = int(os.getenv("TOKEN_MAX_AGE", str(12 * 3600)))
    SEED_DEMO = _bool(os.getenv("SEED_DEMO"), True)
    WATSON_API_KEY = os.getenv("WATSON_API_KEY", "")
    WATSON_URL = os.getenv("WATSON_URL", "")
    WATSON_ASSISTANT_ID = os.getenv("WATSON_ASSISTANT_ID", "")
    WATSON_VERSION = os.getenv("WATSON_VERSION", "2021-06-14")
    WATSON_TIMEOUT = float(os.getenv("WATSON_TIMEOUT", "6"))
    WATSON_ENVIRONMENT_ID = os.getenv("WATSON_ENVIRONMENT_ID", "")
    WATSON_IAM_URL = os.getenv("WATSON_IAM_URL", "https://iam.cloud.ibm.com/identity/token")
    WATSON_CLIENT = None
    PACIENTE_PADRAO = os.getenv("PACIENTE_PADRAO", "p001")
    USUARIOS = {
        "medico": {
            "senha": os.getenv("MEDICO_SENHA", "medico123"),
            "perfil": "medico",
            "nome": "Dra. Demo",
            "paciente_id": None,
        },
        "paciente": {
            "senha": os.getenv("PACIENTE_SENHA", "paciente123"),
            "perfil": "paciente",
            "nome": "Paciente Demo",
            "paciente_id": os.getenv("PACIENTE_PADRAO", "p001"),
        },
    }
    OPERACAO_PADRAO = {
        "carga_sistema": 50.0,
        "tempo_espera": 30.0,
        "disponibilidade_recursos": 70.0,
        "densidade_eventos": 3.0,
    }
    IDADE_PADRAO = 55.0
    SPO2_PADRAO = 96.0
    PA_PADRAO = 125.0
