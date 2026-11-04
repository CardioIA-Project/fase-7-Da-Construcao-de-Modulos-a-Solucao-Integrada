import { useEffect, useRef, useState } from "react";
import { AppState } from "react-native";

interface Estado<T> {
  chave: string;
  dados: T | undefined;
  erro: unknown;
  carregando: boolean;
}

export type ResultadoPolling<T> = Omit<Estado<T>, "chave">;

export function usePolling<T>(
  buscar: () => Promise<T>,
  intervaloMs: number,
  chave: string,
  ativo = true,
): ResultadoPolling<T> {
  const [estado, setEstado] = useState<Estado<T>>({ chave, dados: undefined, erro: null, carregando: true });
  const buscarRef = useRef(buscar);

  useEffect(() => {
    buscarRef.current = buscar;
  });

  useEffect(() => {
    if (!ativo) return;
    let cancelado = false;
    let temporizador: ReturnType<typeof setTimeout> | undefined;

    async function ciclo() {
      if (AppState.currentState === "active") {
        try {
          const dados = await buscarRef.current();
          if (!cancelado) setEstado({ chave, dados, erro: null, carregando: false });
        } catch (erro) {
          if (!cancelado) {
            setEstado((anterior) => ({
              chave,
              dados: anterior.chave === chave ? anterior.dados : undefined,
              erro,
              carregando: false,
            }));
          }
        }
      }
      if (!cancelado) temporizador = setTimeout(ciclo, intervaloMs);
    }

    ciclo();
    return () => {
      cancelado = true;
      clearTimeout(temporizador);
    };
  }, [chave, intervaloMs, ativo]);

  if (estado.chave !== chave) return { dados: undefined, erro: null, carregando: true };
  return estado;
}
