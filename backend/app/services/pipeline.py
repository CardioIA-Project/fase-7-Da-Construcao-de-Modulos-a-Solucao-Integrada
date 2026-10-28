from __future__ import annotations

import random
from datetime import timedelta

from flask import current_app

from ..ml import DadosPaciente, LeituraSensor, analisar
from .store import Store, agora


def montar_dados(store: Store, paciente_id: str, fc_media: float, temperatura: float,
                 spo2_media: float | None, pa_sistolica: float | None) -> DadosPaciente:
    cfg = current_app.config
    paciente = store.obter_paciente(paciente_id)
    operacao = store.operacao()
    return DadosPaciente(
        idade_media=paciente["idade"] if paciente else cfg["IDADE_PADRAO"],
        carga_sistema=operacao["carga_sistema"],
        tempo_espera=operacao["tempo_espera"],
        fc_media=fc_media,
        spo2_media=spo2_media if spo2_media is not None else cfg["SPO2_PADRAO"],
        pa_sistolica=pa_sistolica if pa_sistolica is not None else cfg["PA_PADRAO"],
        temperatura=temperatura,
        densidade_eventos=operacao["densidade_eventos"],
        eventos_24h=store.eventos_24h(paciente_id),
        disponibilidade_recursos=operacao["disponibilidade_recursos"],
    )


def processar_leitura(store: Store, leitura: LeituraSensor) -> dict:
    if store.obter_paciente(leitura.paciente_id) is None:
        store.garantir_paciente(
            leitura.paciente_id, f"Paciente {leitura.paciente_id}", current_app.config["IDADE_PADRAO"]
        )
    dados = montar_dados(
        store,
        leitura.paciente_id,
        leitura.fc_media,
        leitura.temperatura,
        leitura.spo2_media,
        leitura.pa_sistolica,
    )
    resultado = analisar(current_app.config["MODEL_PATH"], dados)
    entrada = {
        "fc_media": dados.fc_media,
        "temperatura": dados.temperatura,
        "spo2_media": dados.spo2_media,
        "pa_sistolica": dados.pa_sistolica,
        "eventos_24h": dados.eventos_24h,
        "dispositivo": leitura.dispositivo,
    }
    return store.salvar_leitura(leitura.paciente_id, entrada, resultado)


def popular_demo(store: Store) -> None:
    cfg = current_app.config
    paciente_id = cfg["PACIENTE_PADRAO"]
    store.garantir_paciente(paciente_id, "Paciente Demo", 58.0)
    store.garantir_paciente("p002", "Paciente Demo 2", 67.0)
    if store.total_leituras() > 0:
        return
    gerador = random.Random(7)
    inicio = agora() - timedelta(minutes=40)
    for passo in range(20):
        momento = inicio + timedelta(minutes=2 * passo)
        fc = round(gerador.uniform(70, 96), 1)
        spo2 = round(gerador.uniform(95, 99), 1)
        temperatura = round(gerador.uniform(23, 26), 1)
        dados = montar_dados(store, paciente_id, fc, temperatura, spo2, 122.0)
        resultado = analisar(cfg["MODEL_PATH"], dados)
        store.salvar_leitura(
            paciente_id,
            {
                "fc_media": dados.fc_media,
                "temperatura": dados.temperatura,
                "spo2_media": dados.spo2_media,
                "pa_sistolica": dados.pa_sistolica,
                "eventos_24h": dados.eventos_24h,
                "dispositivo": "seed",
            },
            resultado,
            criado_em=momento,
        )
