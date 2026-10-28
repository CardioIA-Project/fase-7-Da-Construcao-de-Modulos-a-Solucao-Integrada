from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split


def gerar_base(n: int = 5000, semente: int = 42) -> pd.DataFrame:
    np.random.seed(semente)
    df = pd.DataFrame(
        {
            "idade_media": np.random.normal(55, 12, n).clip(18, 90),
            "carga_sistema": np.random.uniform(30, 100, n),
            "tempo_espera": np.random.normal(45, 20, n).clip(5, 180),
            "fc_media": np.random.normal(85, 15, n).clip(50, 150),
            "spo2_media": np.random.normal(95, 3, n).clip(70, 100),
            "pa_sistolica": np.random.normal(125, 20, n).clip(80, 200),
            "temperatura": np.random.normal(24, 5, n).clip(10, 40),
            "densidade_eventos": np.random.poisson(3, n),
            "eventos_24h": np.random.poisson(2, n),
            "disponibilidade_recursos": np.random.uniform(20, 100, n),
        }
    )
    risk_score = (
        (df["carga_sistema"] > 80).astype(int)
        + (df["tempo_espera"] > 60).astype(int)
        + (df["spo2_media"] < 92).astype(int)
        + (df["fc_media"] > 110).astype(int)
        + (df["eventos_24h"] > 4).astype(int)
        + (df["disponibilidade_recursos"] < 40).astype(int)
    )
    df["pico_risco"] = (risk_score >= 2).astype(int)
    return df


def treinar(caminho: str | Path, verbose: bool = False) -> dict:
    df = gerar_base()
    X = df.drop(columns="pico_risco")
    y = df["pico_risco"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    modelo = RandomForestClassifier(n_estimators=200, random_state=42)
    modelo.fit(X_train, y_train)
    y_pred = modelo.predict(X_test)
    acuracia = float(accuracy_score(y_test, y_pred))
    if verbose:
        print(df["pico_risco"].value_counts(normalize=True))
        print("Acurácia:", acuracia)
        print("Matriz de confusão:\n", confusion_matrix(y_test, y_pred))
        print(classification_report(y_test, y_pred))
    pacote = {"modelo": modelo, "colunas": list(X.columns)}
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pacote, caminho)
    return {"acuracia": acuracia, "caminho": str(caminho)}
