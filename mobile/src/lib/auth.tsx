import * as SecureStore from "expo-secure-store";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { aoNaoAutenticado, api, definirToken } from "./api";
import type { Sessao } from "./types";

const CHAVE = "cardioia.sessao";

interface ContextoAuth {
  sessao: Sessao | null;
  carregando: boolean;
  entrar: (usuario: string, senha: string) => Promise<void>;
  sair: () => Promise<void>;
}

const Contexto = createContext<ContextoAuth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [sessao, setSessao] = useState<Sessao | null>(null);
  const [carregando, setCarregando] = useState(true);

  const sair = useCallback(async () => {
    definirToken(null);
    setSessao(null);
    try {
      await SecureStore.deleteItemAsync(CHAVE);
    } catch {
      return;
    }
  }, []);

  useEffect(() => {
    aoNaoAutenticado(() => {
      sair();
    });
  }, [sair]);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const bruto = await SecureStore.getItemAsync(CHAVE);
        const salva = bruto ? (JSON.parse(bruto) as Sessao) : null;
        if (ativo && salva && typeof salva.token === "string") {
          definirToken(salva.token);
          setSessao(salva);
        }
      } catch {
        definirToken(null);
      } finally {
        if (ativo) setCarregando(false);
      }
    })();
    return () => {
      ativo = false;
    };
  }, []);

  const entrar = useCallback(async (usuario: string, senha: string) => {
    const nova = await api.login(usuario.trim(), senha);
    definirToken(nova.token);
    setSessao(nova);
    try {
      await SecureStore.setItemAsync(CHAVE, JSON.stringify(nova));
    } catch {
      return;
    }
  }, []);

  const valor = useMemo(() => ({ sessao, carregando, entrar, sair }), [sessao, carregando, entrar, sair]);
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useAuth(): ContextoAuth {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error("useAuth fora do AuthProvider");
  return contexto;
}
