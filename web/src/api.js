import { useEffect, useState } from "react";

const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const CHAVE = "cardioia_sessao";

export const sessaoSalva = () => {
  try {
    return JSON.parse(localStorage.getItem(CHAVE));
  } catch {
    return null;
  }
};

export const salvarSessao = (s) => {
  try {
    if (s) localStorage.setItem(CHAVE, JSON.stringify(s));
    else localStorage.removeItem(CHAVE);
  } catch {}
};

export class ApiError extends Error {
  constructor(status, corpo) {
    super(corpo?.erro || "erro_rede");
    this.status = status;
    this.corpo = corpo;
  }
}

export async function api(caminho, { metodo = "GET", corpo, auth = true } = {}) {
  const headers = {};
  if (corpo) headers["Content-Type"] = "application/json";
  const sessao = sessaoSalva();
  if (auth && sessao?.token) headers.Authorization = `Bearer ${sessao.token}`;
  let res;
  try {
    res = await fetch(BASE + caminho, {
      method: metodo,
      headers,
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
  } catch {
    throw new ApiError(0, { erro: "sem_conexao" });
  }
  let dados = null;
  try {
    dados = await res.json();
  } catch {}
  if (res.status === 401 && auth && sessao) window.dispatchEvent(new Event("sessao-expirada"));
  if (!res.ok) throw new ApiError(res.status, dados);
  return dados;
}

export function usePolling(carregar, ms, deps) {
  const [estado, setEstado] = useState({ dados: null, erro: null, carregando: true });
  useEffect(() => {
    let vivo = true;
    setEstado({ dados: null, erro: null, carregando: true });
    const rodar = async () => {
      try {
        const dados = await carregar();
        if (vivo) setEstado({ dados, erro: null, carregando: false });
      } catch (erro) {
        if (vivo) setEstado((e) => ({ dados: erro.status === 404 ? null : e.dados, erro, carregando: false }));
      }
    };
    rodar();
    const t = setInterval(rodar, ms);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, deps);
  return estado;
}
