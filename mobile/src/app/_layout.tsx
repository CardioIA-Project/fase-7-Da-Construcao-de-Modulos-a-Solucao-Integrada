import { Stack } from "expo-router";
import { AuthProvider } from "@/lib/auth";
import { cores } from "@/lib/tema";

export default function LayoutRaiz() {
  return (
    <AuthProvider>
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: cores.marcaEscura },
          headerTintColor: "#FFFFFF",
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="login" options={{ title: "CardioIA", headerShown: false }} />
        <Stack.Screen name="triagem" options={{ title: "Triagem de sintomas" }} />
        <Stack.Screen name="(app)" options={{ headerShown: false }} />
      </Stack>
    </AuthProvider>
  );
}
