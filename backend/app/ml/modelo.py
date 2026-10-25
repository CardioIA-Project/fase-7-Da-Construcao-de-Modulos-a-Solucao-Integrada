from __future__ import annotations

import threading
from pathlib import Path

import joblib
import pandas as pd

from .schemas import DadosPaciente
from .treino import treinar

_trava = threading.Lock()
_cache: dict[str, dict] = {}


def carregar(caminho: str | Path) -> dict:
    chave = str(caminho)
    with _trava:
        if chave not in _cache:
            if not Path(chave).exists():
                treinar(chave)
            _cache[chave] = joblib.load(chave)
        return _cache[chave]


def prever_probabilidade(caminho: str | Path, dados: DadosPaciente) -> float:
    pacote = carregar(caminho)
    linha = pd.DataFrame([dados.model_dump()])[pacote["colunas"]]
    return float(pacote["modelo"].predict_proba(linha)[0, 1])
