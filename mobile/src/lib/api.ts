import type {
  HistoricoResposta,
  Leitura,
  Operacao,
  PacienteResumo,
  RespostaChat,
  Sessao,
} from "./types";

const BASE = (process.env.EXPO_PUBLIC_API_URL ?? "").replace(/\/+$/, "");

export const API_CONFIGURADA = BASE !== "";

export class ApiError extends Error {
  status: number;
  codigo: string;

  constructor(status: number, codigo: string) {
    super(codigo);
    this.status = status;
    this.codigo = codigo;
  }
}

let token: string | null = null;
let aoExpirar: () => void = () => {};

export function definirToken(valor: string | null) {
  token = valor;
}

export function aoNaoAutenticado(funcao: () => void) {
  aoExpirar = funcao;
}

interface Opcoes {
  metodo?: "GET" | "POST" | "PUT" | "DELETE";
  corpo?: unknown;
  autenticado?: boolean;
  limiteMs?: number;
}

async function requisitar<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const { metodo = "GET", corpo, autenticado = true, limiteMs = 20000 } = opcoes;
  if (!API_CONFIGURADA) throw new ApiError(0, "api_nao_configurada");

  const cabecalhos: Record<string, string> = { Accept: "application/json" };
  if (corpo !== undefined) cabecalhos["Content-Type"] = "application/json";
  if (autenticado && token) cabecalhos.Authorization = `Bearer ${token}`;

  const controlador = new AbortController();
  const prazo = setTimeout(() => controlador.abort(), limiteMs);
  let resposta: Response;
  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      signal: controlador.signal,
    });
  } catch {
    throw new ApiError(0, "sem_conexao");
  } finally {
    clearTimeout(prazo);
  }

  let dados: unknown = null;
  try {
    dados = await resposta.json();
  } catch {
    dados = null;
  }

  if (!resposta.ok) {
    const codigo =
      dados && typeof dados === "object" && "erro" in dados
        ? String((dados as { erro: unknown }).erro)
        : "erro_desconhecido";
    if (resposta.status === 401 && autenticado && token) aoExpirar();
    throw new ApiError(resposta.status, codigo);
  }
  return dados as T;
}

export const api = {
  saude: () => requisitar<{ status: string }>("/health", { autenticado: false, limiteMs: 8000 }),

  login: (usuario: string, senha: string) =>
    requisitar<Sessao>("/api/auth/login", {
      metodo: "POST",
      corpo: { usuario, senha },
      autenticado: false,
      limiteMs: 40000,
    }),

  ultimaLeitura: async (pacienteId: string | null): Promise<Leitura | null> => {
    const consulta = pacienteId ? `?paciente_id=${encodeURIComponent(pacienteId)}` : "";
    try {
      return await requisitar<Leitura>(`/api/sinais/ultimo${consulta}`);
    } catch (erro) {
      if (erro instanceof ApiError && erro.status === 404 && erro.codigo === "sem_leituras") {
        return null;
      }
      throw erro;
    }
  },

  historico: (pacienteId: string | null, limite = 40) => {
    const filtro = pacienteId ? `&paciente_id=${encodeURIComponent(pacienteId)}` : "";
    return requisitar<HistoricoResposta>(`/api/sinais/historico?limite=${limite}${filtro}`);
  },

  pacientes: () => requisitar<{ pacientes: PacienteResumo[] }>("/api/pacientes"),

  operacao: () => requisitar<Operacao>("/api/operacao"),

  atualizarOperacao: (valores: Partial<Operacao>) =>
    requisitar<Operacao>("/api/operacao", { metodo: "PUT", corpo: valores }),

  criarSessaoChat: () =>
    requisitar<{ session_id: string }>("/api/session", {
      metodo: "POST",
      autenticado: false,
      limiteMs: 15000,
    }),

  enviarMensagem: (sessionId: string, texto: string) =>
    requisitar<RespostaChat>("/api/message", {
      metodo: "POST",
      corpo: { session_id: sessionId, text: texto },
      autenticado: false,
      limiteMs: 20000,
    }),

  encerrarSessaoChat: (sessionId: string) =>
    requisitar<{ status: string }>(`/api/session/${encodeURIComponent(sessionId)}`, {
      metodo: "DELETE",
      autenticado: false,
    }),
};

export function mensagemDeErro(erro: unknown): string {
  if (!(erro instanceof ApiError)) return "Algo deu errado. Tente novamente.";
  switch (erro.codigo) {
    case "api_nao_configurada":
      return "A URL da API não está configurada (EXPO_PUBLIC_API_URL).";
    case "sem_conexao":
      return "Sem conexão com o servidor. Se ele estava dormindo, aguarde um instante e tente de novo.";
    case "credenciais_invalidas":
      return "Usuário ou senha incorretos.";
    case "acesso_negado":
      return "Você não tem permissão para ver isso.";
    case "nao_autenticado":
      return "Sua sessão expirou. Entre novamente.";
    case "validacao":
      return "Algum valor está fora da faixa permitida.";
    default:
      return "O servidor retornou um erro. Tente novamente.";
  }
}
