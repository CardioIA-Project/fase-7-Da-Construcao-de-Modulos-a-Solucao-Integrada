import { api, usePolling } from "./api";

export const rotulo = { BAIXO: "Baixo", MODERADO: "Moderado", ALTO: "Alto" };
export const hora = (t) => new Date(t).toLocaleString("pt-BR");

export default function Painel({ onAbrir }) {
  const { dados, erro, carregando } = usePolling(() => api("/api/pacientes"), 5000, []);
  const lista = dados?.pacientes || [];

  return (
    <>
      <h1>Pacientes</h1>
      {carregando && <p className="suave">Carregando pacientes</p>}
      {erro && !dados && <p className="erro" role="alert">Não foi possível carregar os pacientes. Verifique a conexão.</p>}
      {!carregando && !erro && lista.length === 0 && <p className="vazio">Nenhum paciente cadastrado ainda.</p>}
      {lista.map((p) => {
        const c = p.ultima_classificacao;
        return (
          <button key={p.id} className={`linha ${c ? c.toLowerCase() : ""}`} onClick={() => onAbrir(p.id)}>
            <span>
              <strong>{p.nome}</strong>
              <br />
              <small className="suave">
                {p.id}
                {p.ultima_atualizacao ? `, atualizado em ${hora(p.ultima_atualizacao)}` : ", sem leituras"}
              </small>
            </span>
            <span>{c ? `${Math.round(p.ultima_probabilidade * 100)}%` : ""}</span>
            <span className={`etq ${c ? c.toLowerCase() : ""}`}>{c ? rotulo[c] : "Sem leitura"}</span>
          </button>
        );
      })}
    </>
  );
}
