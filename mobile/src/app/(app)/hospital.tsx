import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { api, mensagemDeErro } from "@/lib/api";
import { cores } from "@/lib/tema";
import type { Operacao } from "@/lib/types";

const CAMPOS: { chave: keyof Operacao; rotulo: string; maximo: number; ajuda: string }[] = [
  { chave: "carga_sistema", rotulo: "Carga do sistema (%)", maximo: 100, ajuda: "Acima de 80% conta como critério de risco." },
  { chave: "tempo_espera", rotulo: "Tempo de espera (min)", maximo: 1440, ajuda: "Acima de 60 minutos conta como critério de risco." },
  { chave: "disponibilidade_recursos", rotulo: "Disponibilidade de recursos (%)", maximo: 100, ajuda: "Abaixo de 40% conta como critério de risco." },
  { chave: "densidade_eventos", rotulo: "Densidade de eventos", maximo: 100, ajuda: "Entra no cálculo do modelo." },
];

export default function Hospital() {
  const [textos, setTextos] = useState<Record<keyof Operacao, string> | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [salvo, setSalvo] = useState(false);

  useEffect(() => {
    api
      .operacao()
      .then((dados) =>
        setTextos({
          carga_sistema: String(dados.carga_sistema),
          tempo_espera: String(dados.tempo_espera),
          disponibilidade_recursos: String(dados.disponibilidade_recursos),
          densidade_eventos: String(dados.densidade_eventos),
        }),
      )
      .catch((falha) => setErro(mensagemDeErro(falha)));
  }, []);

  async function salvar() {
    if (!textos) return;
    setErro(null);
    setSalvo(false);
    const valores: Partial<Operacao> = {};
    for (const campo of CAMPOS) {
      const numero = Number(textos[campo.chave].replace(",", "."));
      if (!Number.isFinite(numero) || numero < 0 || numero > campo.maximo) {
        setErro(`${campo.rotulo}: use um valor entre 0 e ${campo.maximo}.`);
        return;
      }
      valores[campo.chave] = numero;
    }
    setSalvando(true);
    try {
      await api.atualizarOperacao(valores);
      setSalvo(true);
    } catch (falha) {
      setErro(mensagemDeErro(falha));
    } finally {
      setSalvando(false);
    }
  }

  if (!textos && !erro) return <ActivityIndicator style={{ marginTop: 40 }} color={cores.marca} />;

  return (
    <ScrollView contentContainerStyle={estilos.conteudo} keyboardShouldPersistTaps="handled">
      <Text style={estilos.apoio}>
        Esses parâmetros entram no cálculo do risco das próximas leituras de todos os pacientes.
      </Text>

      {textos &&
        CAMPOS.map((campo) => (
          <View key={campo.chave} style={estilos.campo}>
            <Text style={estilos.rotulo}>{campo.rotulo}</Text>
            <Text style={estilos.apoio}>{campo.ajuda}</Text>
            <TextInput
              style={estilos.entrada}
              value={textos[campo.chave]}
              onChangeText={(valor) => {
                setSalvo(false);
                setTextos({ ...textos, [campo.chave]: valor });
              }}
              keyboardType="decimal-pad"
            />
          </View>
        ))}

      {erro && <Text style={estilos.erro}>{erro}</Text>}
      {salvo && <Text style={estilos.sucesso}>Parâmetros salvos. Valem a partir da próxima leitura.</Text>}

      {textos && (
        <TouchableOpacity style={[estilos.botao, salvando && { opacity: 0.55 }]} onPress={salvar} disabled={salvando}>
          <Text style={estilos.botaoTexto}>{salvando ? "Salvando…" : "Salvar parâmetros"}</Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

const estilos = StyleSheet.create({
  conteudo: { padding: 16, gap: 14 },
  apoio: { color: cores.suave, fontSize: 13 },
  campo: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: 14,
    padding: 14,
    gap: 6,
  },
  rotulo: { fontWeight: "700", color: cores.texto, fontSize: 15 },
  entrada: {
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: cores.texto,
  },
  erro: { color: cores.alto, backgroundColor: cores.altoFundo, padding: 10, borderRadius: 10, fontSize: 13 },
  sucesso: { color: cores.baixo, backgroundColor: cores.baixoFundo, padding: 10, borderRadius: 10, fontSize: 13 },
  botao: { backgroundColor: cores.marca, borderRadius: 999, paddingVertical: 12, alignItems: "center" },
  botaoTexto: { color: "#FFFFFF", fontWeight: "700", fontSize: 16 },
});
