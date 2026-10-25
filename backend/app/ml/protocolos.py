from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .schemas import DadosPaciente

LIMIAR_MODERADO = 0.30
LIMIAR_ALTO = 0.70


def classificar_risco(probabilidade: float) -> str:
    if probabilidade >= LIMIAR_ALTO:
        return "ALTO"
    if probabilidade >= LIMIAR_MODERADO:
        return "MODERADO"
    return "BAIXO"


@dataclass(frozen=True)
class Protocolo:
    id: str
    texto: str
    acao: str
    condicao: Callable[[DadosPaciente, float], bool]


PROTOCOLOS: list[Protocolo] = [
    Protocolo(
        "spo2_critica",
        "Se SPO2 < 88% → iniciar suporte respiratório imediato",
        "Iniciar suporte respiratório imediato ao paciente (oxigênio e avaliação da equipe médica).",
        lambda d, p: d.spo2_media < 88,
    ),
    Protocolo(
        "carga_sistema_alta",
        "Se carga do sistema > 85% → abrir unidades temporárias",
        "Abrir unidades temporárias de atendimento para absorver a demanda.",
        lambda d, p: d.carga_sistema > 85,
    ),
    Protocolo(
        "fc_alta",
        "Se FC > 120 → iniciar monitoramento intensivo",
        "Colocar o paciente em monitoramento intensivo de frequência cardíaca.",
        lambda d, p: d.fc_media > 120,
    ),
    Protocolo(
        "eventos_24h_altos",
        "Se eventos_24h > 5 → ativar equipe de resposta rápida",
        "Ativar a equipe de resposta rápida.",
        lambda d, p: d.eventos_24h > 5,
    ),
    Protocolo(
        "recursos_baixos",
        "Se disponibilidade_recursos < 30% → redistribuir insumos",
        "Redistribuir insumos entre as unidades para recompor os recursos disponíveis.",
        lambda d, p: d.disponibilidade_recursos < 30,
    ),
    Protocolo(
        "espera_longa",
        "Se tempo_espera > 90 min → priorizar triagem emergencial",
        "Priorizar a triagem emergencial para reduzir o tempo de espera.",
        lambda d, p: d.tempo_espera > 90,
    ),
    Protocolo(
        "febre",
        "Se temperatura > 38°C média → iniciar protocolo infeccioso",
        "Iniciar o protocolo infeccioso (isolamento e investigação).",
        lambda d, p: d.temperatura > 38,
    ),
    Protocolo(
        "densidade_eventos_alta",
        "Se densidade_eventos > 6 → ativar plano de contingência",
        "Ativar o plano de contingência da unidade.",
        lambda d, p: d.densidade_eventos > 6,
    ),
    Protocolo(
        "hipotensao",
        "Se PA sistólica < 90 → iniciar protocolo de choque",
        "Iniciar o protocolo de choque.",
        lambda d, p: d.pa_sistolica < 90,
    ),
    Protocolo(
        "risco_sistemico_alto",
        "Se risco sistêmico alto → ativar estado de emergência",
        "Ativar o estado de emergência e comunicar a gestão do hospital.",
        lambda d, p: classificar_risco(p) == "ALTO",
    ),
]

TEXTOS_PROTOCOLOS = {p.texto for p in PROTOCOLOS}


def avaliar_protocolos(paciente: DadosPaciente, probabilidade: float) -> list[Protocolo]:
    return [p for p in PROTOCOLOS if p.condicao(paciente, probabilidade)]
