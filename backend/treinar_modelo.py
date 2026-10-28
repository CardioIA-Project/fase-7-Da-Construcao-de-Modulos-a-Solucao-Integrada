import os
from pathlib import Path

from app.ml.treino import treinar

if __name__ == "__main__":
    destino = os.getenv("MODEL_PATH", str(Path(__file__).resolve().parent / "modelo_risco_cardiaco.pkl"))
    treinar(destino, verbose=True)
