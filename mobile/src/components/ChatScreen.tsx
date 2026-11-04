import { useCallback, useEffect, useRef, useState } from "react";
import {
  KeyboardAvoidingView,
  Linking,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { ApiError, api } from "@/lib/api";
import { cores } from "@/lib/tema";

interface Mensagem {
  id: number;
  texto: string;
  autor: "usuario" | "assistente";
  emergencia: boolean;
}

type Estado = "conectando" | "pronto" | "falhou";

const TENTATIVAS = 6;
const PAUSA_MS = 5000;

function esperar(ms: number) {
  return new Promise((resolver) => setTimeout(resolver, ms));
}

export function ChatScreen() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [opcoes, setOpcoes] = useState<string[]>([]);
  const [texto, setTexto] = useState("");
  const [digitando, setDigitando] = useState(false);
  const [estado, setEstado] = useState<Estado>("conectando");
  const [emergencia, setEmergencia] = useState(false);
  const sessao = useRef<string | null>(null);
  const contador = useRef(0);
  const geracao = useRef(0);
  const rolagem = useRef<ScrollView>(null);

  const adicionar = useCallback((conteudo: string, autor: Mensagem["autor"], alerta = false) => {
    contador.current += 1;
    const id = contador.current;
    setMensagens((anteriores) => [
      ...anteriores,
      { id, texto: conteudo, autor, emergencia: autor === "assistente" && alerta },
    ]);
  }, []);

  const enviar = useCallback(
    async (sessaoId: string, conteudo: string, mostrar: boolean, valida?: number) => {
      if (mostrar) adicionar(conteudo, "usuario");
      setOpcoes([]);
      setDigitando(true);
      try {
        const resposta = await api.enviarMensagem(sessaoId, conteudo);
        if (valida !== undefined && valida !== geracao.current) return true;
        if (resposta.replies.length === 0) adicionar("Não entendi. Pode reformular?", "assistente");
        resposta.replies.forEach((linha) => adicionar(linha, "assistente", resposta.emergencia));
        setOpcoes(resposta.options);
        if (resposta.emergencia) setEmergencia(true);
        return true;
      } catch (falha) {
        if (falha instanceof ApiError && falha.status === 404) return false;
        adicionar("Erro de conexão com o servidor. Tente novamente.", "assistente");
        return true;
      } finally {
        setDigitando(false);
      }
    },
    [adicionar],
  );

  const iniciar = useCallback(async () => {
    geracao.current += 1;
    const minha = geracao.current;
    for (let tentativa = 1; tentativa <= TENTATIVAS; tentativa++) {
      try {
        const { session_id } = await api.criarSessaoChat();
        if (minha !== geracao.current) {
          api.encerrarSessaoChat(session_id).catch(() => undefined);
          return;
        }
        sessao.current = session_id;
        setEstado("pronto");
        await enviar(session_id, "", false, minha);
        return;
      } catch {
        await esperar(PAUSA_MS);
        if (minha !== geracao.current) return;
      }
    }
    setEstado("falhou");
  }, [enviar]);

  const recomecar = useCallback(() => {
    setEstado("conectando");
    setOpcoes([]);
    setEmergencia(false);
    return iniciar();
  }, [iniciar]);

  useEffect(() => {
    iniciar();
    return () => {
      geracao.current += 1;
      if (sessao.current) api.encerrarSessaoChat(sessao.current).catch(() => undefined);
    };
  }, [iniciar]);

  async function responder(conteudo: string) {
    if (!sessao.current || digitando) return;
    const continua = await enviar(sessao.current, conteudo, true);
    if (!continua) {
      adicionar("A conversa expirou. Vou iniciar uma nova.", "assistente");
      await recomecar();
    }
  }

  function aoEnviar() {
    const conteudo = texto.trim();
    if (!conteudo) return;
    setTexto("");
    responder(conteudo);
  }

  function novaTriagem() {
    if (sessao.current) api.encerrarSessaoChat(sessao.current).catch(() => undefined);
    setMensagens([]);
    recomecar();
  }

  const pronto = estado === "pronto";

  return (
    <KeyboardAvoidingView style={estilos.tela} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <View style={estilos.topo}>
        <Text style={estilos.aviso}>Triagem inicial. Não substitui avaliação médica.</Text>
        <TouchableOpacity onPress={novaTriagem} accessibilityRole="button">
          <Text style={estilos.nova}>Nova triagem</Text>
        </TouchableOpacity>
      </View>

      {emergencia && (
        <View style={estilos.emergencia}>
          <Text style={estilos.emergenciaTexto}>Possível emergência cardíaca. Ligue agora para o SAMU.</Text>
          <TouchableOpacity style={estilos.ligar} onPress={() => Linking.openURL("tel:192")}>
            <Text style={estilos.ligarTexto}>Ligar 192</Text>
          </TouchableOpacity>
        </View>
      )}

      <ScrollView
        ref={rolagem}
        style={estilos.janela}
        contentContainerStyle={estilos.conteudo}
        onContentSizeChange={() => rolagem.current?.scrollToEnd({ animated: true })}
      >
        {estado === "conectando" && (
          <Text style={estilos.vazio}>Conectando ao assistente… a primeira conexão pode levar até 1 minuto.</Text>
        )}
        {estado === "falhou" && (
          <View style={estilos.falha}>
            <Text style={estilos.vazio}>Não foi possível conectar ao assistente.</Text>
            <TouchableOpacity style={estilos.botao} onPress={recomecar}>
              <Text style={estilos.botaoTexto}>Tentar novamente</Text>
            </TouchableOpacity>
          </View>
        )}

        {mensagens.map((mensagem) => (
          <View
            key={mensagem.id}
            style={[
              estilos.bolha,
              mensagem.autor === "usuario" ? estilos.bolhaUsuario : estilos.bolhaAssistente,
              mensagem.emergencia && estilos.bolhaEmergencia,
            ]}
          >
            <Text
              style={[
                estilos.bolhaTexto,
                mensagem.autor === "usuario" && { color: "#FFFFFF" },
                mensagem.emergencia && { color: "#8A1F28", fontWeight: "600" },
              ]}
            >
              {mensagem.texto}
            </Text>
          </View>
        ))}

        {!digitando && opcoes.length > 0 && (
          <View style={estilos.opcoes}>
            {opcoes.map((opcao) => (
              <TouchableOpacity key={opcao} style={estilos.opcao} onPress={() => responder(opcao)}>
                <Text style={estilos.opcaoTexto}>{opcao}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {digitando && <Text style={estilos.digitando}>Digitando…</Text>}
      </ScrollView>

      <View style={estilos.envio}>
        <TextInput
          style={estilos.entrada}
          placeholder="Descreva o que você está sentindo…"
          value={texto}
          onChangeText={setTexto}
          onSubmitEditing={aoEnviar}
          returnKeyType="send"
          editable={pronto}
          maxLength={500}
        />
        <TouchableOpacity
          style={[estilos.enviar, (!pronto || digitando) && estilos.enviarOff]}
          onPress={aoEnviar}
          disabled={!pronto || digitando}
          accessibilityLabel="Enviar mensagem"
        >
          <Text style={estilos.enviarTexto}>➤</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const estilos = StyleSheet.create({
  tela: { flex: 1, backgroundColor: cores.superficie },
  topo: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: cores.superficie,
    borderBottomWidth: 1,
    borderBottomColor: cores.borda,
  },
  aviso: { color: cores.suave, fontSize: 12, flex: 1 },
  nova: { color: cores.marca, fontWeight: "600", fontSize: 14 },
  emergencia: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: cores.altoFundo,
    borderBottomWidth: 2,
    borderBottomColor: cores.alto,
    padding: 12,
  },
  emergenciaTexto: { flex: 1, color: "#8A1F28", fontWeight: "600" },
  ligar: { backgroundColor: cores.alto, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999 },
  ligarTexto: { color: "#FFFFFF", fontWeight: "700" },
  janela: { flex: 1, backgroundColor: cores.fundo },
  conteudo: { padding: 16, gap: 10 },
  vazio: { textAlign: "center", color: cores.suave, marginTop: 30 },
  falha: { alignItems: "center", gap: 12 },
  botao: { backgroundColor: cores.marca, paddingHorizontal: 18, paddingVertical: 10, borderRadius: 999 },
  botaoTexto: { color: "#FFFFFF", fontWeight: "600" },
  bolha: { maxWidth: "84%", padding: 12, borderRadius: 14 },
  bolhaAssistente: {
    alignSelf: "flex-start",
    backgroundColor: "#E1F0EF",
    borderWidth: 1,
    borderColor: cores.borda,
  },
  bolhaUsuario: { alignSelf: "flex-end", backgroundColor: cores.marca },
  bolhaEmergencia: { backgroundColor: cores.altoFundo, borderColor: cores.alto },
  bolhaTexto: { fontSize: 15, lineHeight: 20, color: cores.texto },
  opcoes: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  opcao: {
    borderWidth: 1,
    borderColor: cores.marca,
    backgroundColor: cores.superficie,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
  },
  opcaoTexto: { color: cores.marca, fontWeight: "600", fontSize: 14 },
  digitando: { color: cores.suave, fontStyle: "italic" },
  envio: {
    flexDirection: "row",
    gap: 10,
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: cores.borda,
    backgroundColor: cores.superficie,
  },
  entrada: {
    flex: 1,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    color: cores.texto,
  },
  enviar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: cores.marca,
    alignItems: "center",
    justifyContent: "center",
  },
  enviarOff: { backgroundColor: "#B7C6C6" },
  enviarTexto: { color: "#FFFFFF", fontSize: 18 },
});
