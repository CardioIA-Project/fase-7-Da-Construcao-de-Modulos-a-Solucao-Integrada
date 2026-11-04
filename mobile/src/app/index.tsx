import { Redirect } from "expo-router";
import { ActivityIndicator, View } from "react-native";
import { useAuth } from "@/lib/auth";
import { cores } from "@/lib/tema";

export default function Inicio() {
  const { sessao, carregando } = useAuth();
  if (carregando) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: cores.fundo }}>
        <ActivityIndicator color={cores.marca} size="large" />
      </View>
    );
  }
  return <Redirect href={sessao ? "/(app)" : "/login"} />;
}
