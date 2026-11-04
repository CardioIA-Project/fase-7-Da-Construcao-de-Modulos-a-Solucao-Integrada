import { useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { RiscoDetalhe } from "@/components/RiscoDetalhe";
import { usePolling } from "@/hooks/usePolling";
import { api, mensagemDeErro } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { haQuanto, porcentagem } from "@/lib/format";
import { corDoRisco, cores } from "@/lib/tema";

function ListaPacientes({ aoEscolher }: { aoEscolher: (id: string) => void }) {
  const lista = usePolling(() => api.pacientes(), 5000, "pacientes");

  if (lista.carregando) return <Text style={estilos.apoio}>Carregando pacientes…</Text>;
  if (lista.erro && !lista.dados) return <Text style={estilos.apoio}>{mensagemDeErro(lista.erro)}</Text>;

  return (
    <FlatList
      data={lista.dados?.pacientes ?? []}
      keyExtractor={(paciente) => paciente.id}
      contentContainerStyle={estilos.lista}
      ListEmptyComponent={<Text style={estilos.apoio}>Nenhum paciente cadastrado.</Text>}
      renderItem={({ item }) => {
        const { cor, fundo } = corDoRisco(item.ultima_classificacao);
        return (
          <TouchableOpacity
            style={[estilos.linha, { borderLeftColor: cor }]}
            onPress={() => aoEscolher(item.id)}
            accessibilityRole="button"
          >
            <View style={{ flex: 1 }}>
              <Text style={estilos.nome}>{item.nome}</Text>
              <Text style={estilos.apoio}>
                {item.id}
                {item.ultima_atualizacao ? ` · ${haQuanto(item.ultima_atualizacao)}` : " · sem leituras"}
              </Text>
            </View>
            <View style={[estilos.etiqueta, { backgroundColor: fundo }]}>
              <Text style={[estilos.etiquetaTexto, { color: cor }]}>
                {item.ultima_classificacao
                  ? `${item.ultima_classificacao} ${item.ultima_probabilidade !== null ? porcentagem(item.ultima_probabilidade) : ""}`
                  : "Sem leitura"}
              </Text>
            </View>
          </TouchableOpacity>
        );
      }}
    />
  );
}

export default function Painel() {
  const { sessao } = useAuth();
  const [escolhido, setEscolhido] = useState<string | null>(null);

  if (sessao?.perfil !== "medico") return <RiscoDetalhe pacienteId={null} />;

  if (!escolhido) return <ListaPacientes aoEscolher={setEscolhido} />;

  return (
    <View style={{ flex: 1 }}>
      <TouchableOpacity onPress={() => setEscolhido(null)} style={estilos.voltar} accessibilityRole="button">
        <Text style={estilos.voltarTexto}>‹ Voltar à lista</Text>
      </TouchableOpacity>
      <RiscoDetalhe pacienteId={escolhido} />
    </View>
  );
}

const estilos = StyleSheet.create({
  lista: { padding: 16, gap: 10 },
  linha: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderLeftWidth: 5,
    borderRadius: 12,
    padding: 12,
  },
  nome: { fontSize: 16, fontWeight: "700", color: cores.texto },
  apoio: { color: cores.suave, fontSize: 13, padding: 2 },
  etiqueta: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  etiquetaTexto: { fontSize: 12, fontWeight: "700" },
  voltar: { paddingHorizontal: 16, paddingTop: 12 },
  voltarTexto: { color: cores.marca, fontWeight: "600", fontSize: 15 },
});
