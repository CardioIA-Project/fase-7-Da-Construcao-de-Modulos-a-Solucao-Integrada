from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import pm4py
from graphviz.backend import ExecutableNotFound
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.algo.filtering.log.variants import variants_filter
from pm4py.visualization.dfg import visualizer as dfg_visualizer


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "dados" / "event_log_iam.csv"
OUT = ROOT / "evidencias"
OUT.mkdir(exist_ok=True)

PROTOCOLO = [
    "Chegada", "Triagem", "ECG", "Troponina", "Diagnostico IAM",
    "AAS", "Reperfusao", "Alta",
]


def carregar():
    df = pd.read_csv(DATA, parse_dates=["timestamp"])
    return pm4py.format_dataframe(
        df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
    )


def verificar_conformidade(atividades):
    pos = {atividade: i for i, atividade in enumerate(atividades)}
    problemas = []
    if "ECG" not in pos:
        problemas.append("ECG ausente")
    if "Troponina" not in pos:
        problemas.append("Troponina ausente")
    if pos.get("ECG", -1) > pos.get("Troponina", len(atividades)):
        problemas.append("Troponina antes do ECG")
    if "AAS" not in pos:
        problemas.append("AAS ausente")
    if "Reperfusao" not in pos:
        problemas.append("Reperfusao ausente")
    for anterior, posterior in zip(PROTOCOLO, PROTOCOLO[1:]):
        if anterior in pos and posterior in pos and pos[anterior] > pos[posterior]:
            problemas.append(f"ordem invertida: {anterior} antes de {posterior}")
    return problemas


def main():
    log = carregar()
    df = log.sort_values(["case_id", "time:timestamp"]).copy()
    df["next_timestamp"] = df.groupby("case:concept:name")["time:timestamp"].shift(-1)
    df["time_to_next_minutes"] = (
        df["next_timestamp"] - df["time:timestamp"]
    ).dt.total_seconds() / 60
    df.to_csv(OUT / "event_log_iam_enriched.csv", index=False)
    variantes = variants_filter.get_variants(log)
    with (OUT / "variantes.txt").open("w", encoding="utf-8") as arquivo:
        for numero, (trace, casos) in enumerate(variantes.items(), 1):
            atividades = list(trace)
            arquivo.write(f"V{numero} | casos={len(casos)} | {' > '.join(atividades)}\n")
    ciclos = df.groupby("case:concept:name")["time:timestamp"].agg(inicio="min", fim="max")
    ciclos["tempo_ciclo_horas"] = (
        ciclos["fim"] - ciclos["inicio"]
    ).dt.total_seconds() / 3600
    ciclos.to_csv(OUT / "tempos_ciclo.csv")
    df["proxima_atividade"] = df.groupby("case:concept:name")["concept:name"].shift(-1)
    df["tempo_entre_atividades_min"] = df["time_to_next_minutes"]
    gargalos = (
        df.dropna(subset=["proxima_atividade"])
        .groupby(["concept:name", "proxima_atividade"])["tempo_entre_atividades_min"]
        .agg(["count", "mean", "median", "max"])
        .sort_values("mean", ascending=False)
    )
    gargalos.to_csv(OUT / "tempos_entre_atividades.csv")
    conformidade = []
    for case_id, grupo in df.groupby("case:concept:name"):
        atividades = grupo["concept:name"].tolist()
        problemas = verificar_conformidade(atividades)
        conformidade.append({
            "case_id": case_id, "conforme": not problemas,
            "problemas": "; ".join(problemas) or "Nenhum",
        })
    pd.DataFrame(conformidade).to_csv(OUT / "conformidade.csv", index=False)
    case_summary = (
        df.groupby("case:concept:name")
        .agg(
            inicio=("time:timestamp", "min"),
            fim=("time:timestamp", "max"),
            total_eventos=("concept:name", "count"),
        )
        .reset_index(names="case_id")
    )
    case_summary["tempo_ciclo_horas"] = (
        case_summary["fim"] - case_summary["inicio"]
    ).dt.total_seconds() / 3600
    case_summary.to_csv(OUT / "resumo_por_caso.csv", index=False)
    activity_waits = (
        df.dropna(subset=["time_to_next_minutes"])
        .groupby("concept:name")
        .agg(
            media_minutos=("time_to_next_minutes", "mean"),
            mediana_minutos=("time_to_next_minutes", "median"),
            maximo_minutos=("time_to_next_minutes", "max"),
            ocorrencias=("concept:name", "count"),
        )
        .reset_index(names="atividade")
        .sort_values("media_minutos", ascending=False)
    )
    activity_waits.to_csv(OUT / "tempos_por_atividade.csv", index=False)
    dfg = dfg_discovery.apply(log)
    dfg_performance = dfg_discovery.apply(
        log, variant=dfg_discovery.Variants.PERFORMANCE
    )
    parameters = {
        dfg_visualizer.Variants.FREQUENCY.value.Parameters.FORMAT: "png",
        dfg_visualizer.Variants.FREQUENCY.value.Parameters.BGCOLOR: "white",
    }
    try:
        figura = dfg_visualizer.apply(
            dfg_performance, log=log, variant=dfg_visualizer.Variants.PERFORMANCE,
            parameters=parameters,
        )
        dfg_visualizer.save(figura, str(OUT / "performance_dfg.png"))
    except ExecutableNotFound:
        grafo = nx.DiGraph()
        for (origem, destino), media_minutos in dfg_performance.items():
            grafo.add_edge(origem, destino, media_minutos=media_minutos)
        posicoes = nx.spring_layout(grafo, seed=7)
        plt.figure(figsize=(14, 8))
        nx.draw_networkx(grafo, posicoes, node_color="#d9edf7", node_size=2400,
                         arrows=True, font_size=9)
        rotulos = {
            aresta: f"{valor / 60:.1f} min"
            for aresta, valor in nx.get_edge_attributes(grafo, "media_minutos").items()
        }
        nx.draw_networkx_edge_labels(grafo, posicoes, edge_labels=rotulos, font_size=9)
        plt.title("DFG de performance — tempo médio entre atividades")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(OUT / "performance_dfg.png", dpi=160)
        plt.close()
    heuristics_miner.apply(log)
    net, initial_marking, final_marking = pm4py.discover_petri_net_heuristics(log)
    replay = pm4py.conformance_diagnostics_token_based_replay(
        log, net, initial_marking, final_marking
    )
    pd.DataFrame(
        {
            "case_id": list(df["case:concept:name"].drop_duplicates()),
            "trace_is_fit": [item.get("trace_is_fit") for item in replay],
            "missing_tokens": [item.get("missing_tokens") for item in replay],
            "consumed_tokens": [item.get("consumed_tokens") for item in replay],
            "remaining_tokens": [item.get("remaining_tokens") for item in replay],
        }
    ).to_csv(OUT / "token_replay.csv", index=False)
    alignment_net, alignment_im, alignment_fm = pm4py.discover_petri_net_inductive(log)
    alignments = pm4py.conformance_diagnostics_alignments(
        log, alignment_net, alignment_im, alignment_fm
    )
    pd.DataFrame(
        {
            "case_id": list(df["case:concept:name"].drop_duplicates()),
            "cost": [item.get("cost") for item in alignments],
        }
    ).to_csv(OUT / "alignments.csv", index=False)
    fitness = pm4py.fitness_token_based_replay(
        log, net, initial_marking, final_marking
    )
    pd.DataFrame(
        {
            "metric": list(fitness.keys()),
            "value": list(fitness.values()),
        }
    ).to_csv(OUT / "fitness.csv", index=False)
    pm4py.write_xes(log, str(OUT / "event_log_iam.xes"))
    print("Variantes:")
    print((OUT / "variantes.txt").read_text(encoding="utf-8"))
    print("Ciclo (horas):")
    print(ciclos["tempo_ciclo_horas"].describe().to_string())
    print("Conformidade:")
    print(pd.DataFrame(conformidade).to_string(index=False))
    print(f"Evidencias salvas em: {OUT}")


if __name__ == "__main__":
    main()
