import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import { Text, TouchableOpacity } from "react-native";
import { useAuth } from "@/lib/auth";
import { cores } from "@/lib/tema";

export default function LayoutApp() {
  const { sessao, carregando, sair } = useAuth();

  if (carregando) return null;
  if (!sessao) return <Redirect href="/login" />;

  const ehMedico = sessao.perfil === "medico";

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: cores.marcaEscura },
        headerTintColor: "#FFFFFF",
        tabBarActiveTintColor: cores.marca,
        headerRight: () => (
          <TouchableOpacity onPress={sair} style={{ paddingHorizontal: 16 }} accessibilityRole="button">
            <Text style={{ color: "#FFFFFF", fontWeight: "600" }}>Sair</Text>
          </TouchableOpacity>
        ),
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: ehMedico ? "Pacientes" : "Meu painel",
          tabBarIcon: ({ color, size }: { color: string; size: number }) => (
            <Ionicons name="pulse" color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="triagem"
        options={{
          title: "Triagem",
          tabBarIcon: ({ color, size }: { color: string; size: number }) => (
            <Ionicons name="chatbubbles" color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="hospital"
        options={{
          title: "Hospital",
          href: ehMedico ? undefined : null,
          tabBarIcon: ({ color, size }: { color: string; size: number }) => (
            <Ionicons name="business" color={color} size={size} />
          ),
        }}
      />
    </Tabs>
  );
}
