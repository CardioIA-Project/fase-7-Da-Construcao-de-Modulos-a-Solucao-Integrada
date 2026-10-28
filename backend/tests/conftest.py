import os
import sys
from pathlib import Path

import pytest

os.environ["CARDIOIA_IGNORAR_ENV"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.ml.treino import treinar


@pytest.fixture(scope="session")
def caminho_modelo(tmp_path_factory):
    destino = tmp_path_factory.mktemp("modelo") / "modelo.pkl"
    treinar(destino)
    return str(destino)


@pytest.fixture()
def app(tmp_path, caminho_modelo):
    return create_app(
        {
            "TESTING": True,
            "DB_PATH": str(tmp_path / "teste.db"),
            "MODEL_PATH": caminho_modelo,
            "SEED_DEMO": False,
            "SECRET_KEY": "segredo-de-teste",
            "DEVICE_API_KEY": "chave-de-teste",
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def cabecalho_dispositivo():
    return {"X-Device-Key": "chave-de-teste"}


def _login(client, usuario, senha):
    resposta = client.post("/api/auth/login", json={"usuario": usuario, "senha": senha})
    return {"Authorization": f"Bearer {resposta.get_json()['token']}"}


@pytest.fixture()
def cabecalho_medico(client):
    return _login(client, "medico", "medico123")


@pytest.fixture()
def cabecalho_paciente(client):
    return _login(client, "paciente", "paciente123")
