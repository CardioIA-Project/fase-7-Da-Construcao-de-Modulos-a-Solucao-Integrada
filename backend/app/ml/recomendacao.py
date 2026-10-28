from __future__ import annotations

from .modelo import prever_probabilidade
from .protocolos import avaliar_protocolos, classificar_risco
from .schemas import DadosPaciente

AVISO = "Protótipo acadêmico com dados sintéticos. Não substitui avaliação médica."

CRITERIOS = [
    ("Carga do sistema acima de 80%", lambda d: d.carga_sistema > 80),
    ("Tempo de espera acima de 60 min", lambda d: d.tempo_espera > 60),
    ("SpO2 abaixo de 92%", lambda d: d.spo2_media < 92),
    ("Frequência cardíaca acima de 110 bpm", lambda d: d.fc_media > 110),
    ("Mais de 4 eventos nas últimas 24h", lambda d: d.eventos_24h > 4),
    ("Disponibilidade de recursos abaixo de 40%", lambda d: d.disponibilidade_recursos < 40),
]


def fatores_de_risco(dados: DadosPaciente) -> list[str]:
    return [nome for nome, teste in CRITERIOS if teste(dados)]


def montar_recomendacao(classificacao: str, probabilidade: float, acoes: list[str]) -> str:
    percentual = f"{probabilidade * 100:.0f}%"
    if classificacao == "ALTO":
        base = f"Risco ALTO de pico de crise ({percentual}). Acionar a equipe médica imediatamente."
    elif classificacao == "MODERADO":
        base = f"Risco MODERADO de pico de crise ({percentual}). Reforçar o monitoramento e manter a equipe de prontidão."
    else:
        base = f"Risco BAIXO de pico de crise ({percentual}). Manter o monitoramento de rotina."
    if acoes:
        return base + " Ações: " + " ".join(acoes)
    return base


def analisar(caminho_modelo: str, dados: DadosPaciente) -> dict:
    probabilidade = prever_probabilidade(caminho_modelo, dados)
    classificacao = classificar_risco(probabilidade)
    protocolos = avaliar_protocolos(dados, probabilidade)
    return {
        "probabilidade_crise": round(probabilidade, 4),
        "classificacao": classificacao,
        "fatores": fatores_de_risco(dados),
        "protocolos": [{"id": p.id, "texto": p.texto, "acao": p.acao} for p in protocolos],
        "recomendacao": montar_recomendacao(
            classificacao, probabilidade, [p.acao for p in protocolos]
        ),
        "origem": "deterministico",
        "aviso": AVISO,
    }
