from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pacientes (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    idade REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS leituras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    fc_media REAL NOT NULL,
    temperatura REAL NOT NULL,
    spo2_media REAL NOT NULL,
    pa_sistolica REAL NOT NULL,
    eventos_24h REAL NOT NULL,
    probabilidade REAL NOT NULL,
    classificacao TEXT NOT NULL,
    resultado TEXT NOT NULL,
    dispositivo TEXT
);
CREATE INDEX IF NOT EXISTS idx_leituras_paciente ON leituras (paciente_id, criado_em);
CREATE TABLE IF NOT EXISTS operacao (
    chave TEXT PRIMARY KEY,
    valor REAL NOT NULL
);
"""


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Store:
    def __init__(self, caminho: str, operacao_padrao: dict[str, float]) -> None:
        self.caminho = caminho
        self._trava = threading.Lock()
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        with self._conectar() as con:
            con.executescript(ESQUEMA)
            for chave, valor in operacao_padrao.items():
                con.execute("INSERT OR IGNORE INTO operacao (chave, valor) VALUES (?, ?)", (chave, valor))

    def _conectar(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.caminho, timeout=10)
        con.row_factory = sqlite3.Row
        return con

    def garantir_paciente(self, paciente_id: str, nome: str, idade: float) -> None:
        with self._trava, self._conectar() as con:
            con.execute(
                "INSERT OR IGNORE INTO pacientes (id, nome, idade) VALUES (?, ?, ?)",
                (paciente_id, nome, idade),
            )

    def obter_paciente(self, paciente_id: str) -> dict | None:
        with self._conectar() as con:
            linha = con.execute("SELECT * FROM pacientes WHERE id = ?", (paciente_id,)).fetchone()
        return dict(linha) if linha else None

    def listar_pacientes(self) -> list[dict]:
        with self._conectar() as con:
            return [dict(l) for l in con.execute("SELECT * FROM pacientes ORDER BY id")]

    def operacao(self) -> dict[str, float]:
        with self._conectar() as con:
            return {l["chave"]: l["valor"] for l in con.execute("SELECT chave, valor FROM operacao")}

    def atualizar_operacao(self, valores: dict[str, float]) -> dict[str, float]:
        with self._trava, self._conectar() as con:
            for chave, valor in valores.items():
                con.execute("UPDATE operacao SET valor = ? WHERE chave = ?", (valor, chave))
        return self.operacao()

    def eventos_24h(self, paciente_id: str) -> int:
        limite = (agora() - timedelta(hours=24)).isoformat()
        with self._conectar() as con:
            linhas = con.execute(
                "SELECT classificacao FROM leituras WHERE paciente_id = ? AND criado_em >= ? "
                "ORDER BY criado_em, id",
                (paciente_id, limite),
            ).fetchall()
        episodios = 0
        anterior = "BAIXO"
        for linha in linhas:
            atual = linha["classificacao"]
            if atual == "ALTO" and anterior != "ALTO":
                episodios += 1
            anterior = atual
        return episodios

    def salvar_leitura(self, paciente_id: str, entrada: dict, resultado: dict,
                       criado_em: datetime | None = None) -> dict:
        momento = (criado_em or agora()).isoformat()
        with self._trava, self._conectar() as con:
            cursor = con.execute(
                "INSERT INTO leituras (paciente_id, criado_em, fc_media, temperatura, spo2_media, "
                "pa_sistolica, eventos_24h, probabilidade, classificacao, resultado, dispositivo) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    paciente_id,
                    momento,
                    entrada["fc_media"],
                    entrada["temperatura"],
                    entrada["spo2_media"],
                    entrada["pa_sistolica"],
                    entrada["eventos_24h"],
                    resultado["probabilidade_crise"],
                    resultado["classificacao"],
                    json.dumps(resultado, ensure_ascii=False),
                    entrada.get("dispositivo"),
                ),
            )
            leitura_id = cursor.lastrowid
        return self._formatar(
            {
                "id": leitura_id,
                "paciente_id": paciente_id,
                "criado_em": momento,
                "fc_media": entrada["fc_media"],
                "temperatura": entrada["temperatura"],
                "spo2_media": entrada["spo2_media"],
                "pa_sistolica": entrada["pa_sistolica"],
                "eventos_24h": entrada["eventos_24h"],
                "resultado": json.dumps(resultado, ensure_ascii=False),
                "dispositivo": entrada.get("dispositivo"),
            }
        )

    def _formatar(self, linha: dict) -> dict:
        resultado = json.loads(linha["resultado"])
        return {
            "id": linha["id"],
            "paciente_id": linha["paciente_id"],
            "timestamp": linha["criado_em"],
            "dispositivo": linha["dispositivo"],
            "sinais": {
                "fc_media": linha["fc_media"],
                "temperatura": linha["temperatura"],
                "spo2_media": linha["spo2_media"],
                "pa_sistolica": linha["pa_sistolica"],
                "eventos_24h": linha["eventos_24h"],
            },
            **resultado,
        }

    def ultima_leitura(self, paciente_id: str) -> dict | None:
        with self._conectar() as con:
            linha = con.execute(
                "SELECT * FROM leituras WHERE paciente_id = ? ORDER BY criado_em DESC, id DESC LIMIT 1",
                (paciente_id,),
            ).fetchone()
        return self._formatar(dict(linha)) if linha else None

    def historico(self, paciente_id: str, limite: int = 50) -> list[dict]:
        with self._conectar() as con:
            linhas = con.execute(
                "SELECT * FROM leituras WHERE paciente_id = ? ORDER BY criado_em DESC, id DESC LIMIT ?",
                (paciente_id, limite),
            ).fetchall()
        return [self._formatar(dict(l)) for l in reversed(linhas)]

    def total_leituras(self) -> int:
        with self._conectar() as con:
            return con.execute("SELECT COUNT(*) FROM leituras").fetchone()[0]
