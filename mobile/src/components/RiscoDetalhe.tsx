import { ScrollView, StyleSheet, Text, View } from "react-native";
import { Grafico } from "@/components/Grafico";
import { usePolling } from "@/hooks/usePolling";
import { api, mensagemDeErro } from "@/lib/api";
import { haQuanto, numero, porcentagem } from "@/lib/format";
import { corDoRisco, cores } from "@/lib/tema";
import { ApiError } from "@/lib/api";

const ROTULO = { BAIXO: "Risco baixo", MODERADO: "Risco moderado", ALTO: "Risco alto" } as const;

function Sinal({ rotulo, valor, alerta }: { rotulo: string; valor: string; alerta?: boolean }) {
  return (
    <View style={[estilos.sinal, alerta && estilos.sinalAlerta]}>
      <Text style={estilos.sinalRotulo}>{rotulo}</Text>
      <Text style={[estilos.sinalValor, alerta && { color: cores.alto }]}>{valor}</Text>
    </View>
  );
}

export function RiscoDetalhe({ pacienteId }: { pacienteId: string | null }) {
  const chave = pacienteId ?? "proprio";
  const ultima = usePolling(() => api.ultimaLeitura(pacienteId), 3000, `ultima-${chave}`);
  const historico = usePolling(() => api.historico(pacienteId, 40), 10000, `historico-${chave}`);

  const leitura = ultima.dados ?? null;
  const falha = Boolean(ultima.erro) && !(ultima.erro instanceof ApiError && ultima.erro.status === 404);

  if (ultima.carregando) {
    return <Text style={estilos.apoio}>Carregando a última leitura…</Text>;
  }

  return (
    <ScrollView contentContainerStyle={estilos.conteudo}>
      {falha && (
        <Text style={estilos.aviso}>
          Não foi possível atualizar agora. {mensagemDeErro(ultima.erro)}
        </Text>
      )}

      {!leitura ? (
        <View style={estilos.cartao}>
          <Text style={estilos.titulo}>Aguardando a primeira leitura</Text>
          <Text style={estilos.apoio}>
            Quando o sensor enviar dados, o risco e a recomendação aparecem aqui, atualizados sozinhos.
          </Text>
        </View>
      ) : (
        <>
          <View
            style={[
              estilos.faixa,
              { backgroundColor: corDoRisco(leitura.classificacao).fundo, borderColor: corDoRisco(leitura.classificacao).cor },
            ]}
            accessibilityLiveRegion="polite"
          >
            <Text style={[estilos.risco, { color: corDoRisco(leitura.classificacao).cor }]}>
              {ROTULO[leitura.classificacao]}
            </Text>
            <Text style={[estilos.probabilidade, { color: corDoRisco(leitura.classificacao).cor }]}>
              {porcentagem(leitura.probabilidade_crise)}
            </Text>
            <View style={estilos.trilho}>
              <View
                style={[
                  estilos.preenchimento,
                  {
                    width: `${Math.round(leitura.probabilidade_crise * 100)}%`,
                    backgroundColor: corDoRisco(leitura.classificacao).cor,
                  },
                ]}
              />
            </View>
            <Text style={estilos.apoio}>
              Paciente {leitura.paciente_id} · {haQuanto(leitura.timestamp)}
              {leitura.dispositivo ? ` · ${leitura.dispositivo}` : ""}
            </Text>
          </View>

          <Text style={estilos.recomendacao}>{leitura.recomendacao}</Text>

          <View style={estilos.grade}>
            <Sinal rotulo="Freq. cardíaca" valor={`${numero(leitura.sinais.fc_media)} bpm`} alerta={leitura.sinais.fc_media > 110} />
            <Sinal rotulo="SpO2" valor={`${numero(leitura.sinais.spo2_media, 1)}%`} alerta={leitura.sinais.spo2_media < 92} />
            <Sinal rotulo="Temperatura" valor={`${numero(leitura.sinais.temperatura, 1)} °C`} />
            <Sinal rotulo="Pressão sistólica" valor={`${numero(leitura.sinais.pa_sistolica)} mmHg`} />
            <Sinal rotulo="Crises em 24 h" valor={numero(leitura.sinais.eventos_24h)} alerta={leitura.sinais.eventos_24h > 4} />
          </View>

          <View style={estilos.cartao}>
            <Text style={estilos.titulo}>O que pesou no risco</Text>
            {leitura.fatores.length === 0 ? (
              <Text style={estilos.apoio}>Nenhum fator crítico nesta leitura.</Text>
            ) : (
              leitura.fatores.map((fator) => (
                <Text key={fator} style={estilos.item}>
                  • {fator}
                </Text>
              ))
            )}
          </View>

          <View style={estilos.cartao}>
            <Text style={estilos.titulo}>Protocolos acionados</Text>
            {leitura.protocolos.length === 0 ? (
              <Text style={estilos.apoio}>Nenhum protocolo acionado.</Text>
            ) : (
              leitura.protocolos.map((protocolo) => (
                <View key={protocolo.id} style={estilos.protocolo}>
                  <Text style={estilos.protocoloTitulo}>{protocolo.texto}</Text>
                  <Text style={estilos.apoio}>{protocolo.acao}</Text>
                </View>
              ))
            )}
          </View>
        </>
      )}

      <View style={estilos.cartao}>
        <Text style={estilos.titulo}>Probabilidade ao longo do tempo</Text>
        <Grafico leituras={historico.dados?.leituras ?? []} />
      </View>

      <Text style={estilos.rodape}>Protótipo acadêmico com dados sintéticos. Não substitui avaliação médica.</Text>
    </ScrollView>
  );
}

const estilos = StyleSheet.create({
  conteudo: { padding: 16, gap: 14 },
  aviso: { backgroundColor: cores.moderadoFundo, color: cores.moderado, padding: 10, borderRadius: 10, fontSize: 13 },
  faixa: { borderWidth: 2, borderRadius: 14, padding: 16, gap: 6 },
  risco: { fontSize: 20, fontWeight: "700" },
  probabilidade: { fontSize: 44, fontWeight: "700" },
  trilho: { height: 8, borderRadius: 999, backgroundColor: "rgba(0,0,0,0.08)", overflow: "hidden" },
  preenchimento: { height: 8, borderRadius: 999 },
  recomendacao: { fontSize: 15, lineHeight: 21, color: cores.texto },
  grade: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  sinal: {
    flexGrow: 1,
    flexBasis: "30%",
    minWidth: 100,
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: 12,
    padding: 12,
  },
  sinalAlerta: { backgroundColor: cores.altoFundo, borderColor: cores.alto },
  sinalRotulo: { color: cores.suave, fontSize: 12 },
  sinalValor: { fontSize: 18, fontWeight: "700", color: cores.texto, marginTop: 2 },
  cartao: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: 14,
    padding: 14,
    gap: 8,
  },
  titulo: { fontSize: 16, fontWeight: "700", color: cores.texto },
  item: { fontSize: 14, color: cores.texto },
  protocolo: { gap: 2 },
  protocoloTitulo: { fontSize: 14, fontWeight: "700", color: cores.texto },
  apoio: { color: cores.suave, fontSize: 13 },
  rodape: { color: cores.suave, fontSize: 11, textAlign: "center", marginTop: 4 },
});
