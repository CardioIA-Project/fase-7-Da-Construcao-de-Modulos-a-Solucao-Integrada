import { Link, Redirect, useRouter } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { mensagemDeErro } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cores } from "@/lib/tema";

export default function Login() {
  const { sessao, entrar } = useAuth();
  const roteador = useRouter();
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  if (sessao) return <Redirect href="/(app)" />;

  async function aoEntrar() {
    setErro(null);
    setEnviando(true);
    try {
      await entrar(usuario, senha);
      roteador.replace("/(app)");
    } catch (falha) {
      setErro(mensagemDeErro(falha));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <SafeAreaView style={estilos.tela}>
      <KeyboardAvoidingView style={estilos.centro} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <Text style={estilos.marca}>CardioIA</Text>
        <Text style={estilos.apoio}>Acompanhe o risco cardíaco em tempo real.</Text>

        <View style={estilos.cartao}>
          <Text style={estilos.rotulo}>Usuário</Text>
          <TextInput
            style={estilos.entrada}
            value={usuario}
            onChangeText={setUsuario}
            autoCapitalize="none"
            autoCorrect={false}
            textContentType="username"
          />
          <Text style={estilos.rotulo}>Senha</Text>
          <TextInput
            style={estilos.entrada}
            value={senha}
            onChangeText={setSenha}
            secureTextEntry
            textContentType="password"
            onSubmitEditing={aoEntrar}
          />

          {erro && <Text style={estilos.erro}>{erro}</Text>}

          <TouchableOpacity
            style={[estilos.botao, (enviando || !usuario || !senha) && estilos.botaoOff]}
            onPress={aoEntrar}
            disabled={enviando || !usuario || !senha}
          >
            {enviando ? <ActivityIndicator color="#FFFFFF" /> : <Text style={estilos.botaoTexto}>Entrar</Text>}
          </TouchableOpacity>

          {enviando && <Text style={estilos.apoio}>Se o servidor estava dormindo, pode levar até 1 minuto.</Text>}
        </View>

        <Link href="/triagem" style={estilos.link}>
          Fazer triagem de sintomas sem entrar
        </Link>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  tela: { flex: 1, backgroundColor: cores.fundo },
  centro: { flex: 1, justifyContent: "center", padding: 20, gap: 12 },
  marca: { fontSize: 32, fontWeight: "700", color: cores.marcaEscura, textAlign: "center" },
  apoio: { color: cores.suave, fontSize: 13, textAlign: "center" },
  cartao: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: 14,
    padding: 16,
    gap: 8,
  },
  rotulo: { fontWeight: "600", color: cores.texto, fontSize: 14 },
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
  botao: {
    backgroundColor: cores.marca,
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: "center",
    marginTop: 6,
  },
  botaoOff: { opacity: 0.55 },
  botaoTexto: { color: "#FFFFFF", fontWeight: "700", fontSize: 16 },
  link: { color: cores.marca, textAlign: "center", fontWeight: "600", marginTop: 8 },
});
