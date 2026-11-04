import { StyleSheet, Text, View } from "react-native";
import { corDoRisco, cores } from "@/lib/tema";
import type { Leitura } from "@/lib/types";

const ALTURA = 130;

export function Grafico({ leituras }: { leituras: Leitura[] }) {
  if (leituras.length === 0) {
    return <Text style={estilos.vazio}>Ainda não há leituras para montar o gráfico.</Text>;
  }

  return (
    <View>
      <View
        style={estilos.area}
        accessible
        accessibilityLabel={`Probabilidade de crise nas últimas ${leituras.length} leituras`}
      >
        <View style={[estilos.linha, { bottom: ALTURA * 0.7, borderColor: cores.alto }]} />
        <View style={[estilos.linha, { bottom: ALTURA * 0.3, borderColor: cores.moderado }]} />
        <View style={estilos.barras}>
          {leituras.map((leitura) => (
            <View
              key={leitura.id}
              style={[
                estilos.barra,
                {
                  height: Math.max(2, leitura.probabilidade_crise * ALTURA),
                  backgroundColor: corDoRisco(leitura.classificacao).cor,
                },
              ]}
            />
          ))}
        </View>
      </View>
      <Text style={estilos.legenda}>Linha vermelha: risco alto (70%). Linha amarela: risco moderado (30%).</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  area: {
    height: ALTURA,
    borderBottomWidth: 1,
    borderBottomColor: cores.borda,
    justifyContent: "flex-end",
  },
  barras: { flexDirection: "row", alignItems: "flex-end", gap: 2, height: ALTURA },
  barra: { flex: 1, borderTopLeftRadius: 2, borderTopRightRadius: 2 },
  linha: { position: "absolute", left: 0, right: 0, borderTopWidth: 1, borderStyle: "dashed" },
  legenda: { color: cores.suave, fontSize: 11, marginTop: 6 },
  vazio: { color: cores.suave, fontSize: 14 },
});
