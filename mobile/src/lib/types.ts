export type Classificacao = "BAIXO" | "MODERADO" | "ALTO";
export type Perfil = "medico" | "paciente";

export interface Sessao {
  token: string;
  perfil: Perfil;
  paciente_id: string | null;
  nome: string;
  usuario: string;
}

export interface Protocolo {
  id: string;
  texto: string;
  acao: string;
}

export interface Sinais {
  fc_media: number;
  temperatura: number;
  spo2_media: number;
  pa_sistolica: number;
  eventos_24h: number;
}

export interface Leitura {
  id: number;
  paciente_id: string;
  dispositivo: string | null;
  timestamp: string;
  classificacao: Classificacao;
  probabilidade_crise: number;
  fatores: string[];
  protocolos: Protocolo[];
  recomendacao: string;
  aviso: string;
  origem: string;
  sinais: Sinais;
}

export interface HistoricoResposta {
  paciente_id: string;
  leituras: Leitura[];
}

export interface PacienteResumo {
  id: string;
  nome: string;
  idade: number;
  ultima_atualizacao: string | null;
  ultima_classificacao: Classificacao | null;
  ultima_probabilidade: number | null;
}

export interface Operacao {
  carga_sistema: number;
  tempo_espera: number;
  disponibilidade_recursos: number;
  densidade_eventos: number;
}

export interface RespostaChat {
  replies: string[];
  options: string[];
  emergencia: boolean;
  finalizado: boolean;
  origem: "watson" | "local";
}
