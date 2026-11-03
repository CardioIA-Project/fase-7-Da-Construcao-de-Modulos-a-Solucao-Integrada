import { useEffect, useState } from "react";
import { api } from "./api";

const campos = [
  ["carga_sistema", "Carga do sistema (0 a 100)", 100],
  ["tempo_espera", "Tempo de espera em minutos (0 a 1440)", 1440],
  ["disponibilidade_recursos", "Disponibilidade de recursos (0 a 100)", 100],
  ["densidade_eventos", "Densidade de eventos (0 a 100)", 100],
];

export default function Operacao() {
  const [valores, setValores] = useState(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    api("/api/operacao")
      .then(setValores)
      .catch(() => setStatus("Não foi possível carregar os parâmetros."));
  }, []);

  const salvar = async (e) => {
    e.preventDefault();
    setStatus("");
    const corpo = {};
    campos.forEach(([k]) => (corpo[k] = Number(valores[k])));
    try {
      setValores(await api("/api/operacao", { metodo: "PUT", corpo }));
      setStatus("Parâmetros salvos. As próximas leituras usam estes valores.");
    } catch (err) {
      setStatus(err.status === 422 ? "Algum valor está fora da faixa permitida." : "Não foi possível salvar. Tente de novo.");
    }
  };

  return (
    <>
      <h1>Situação do hospital</h1>
      <p className="suave">Estes valores entram no cálculo de risco de todas as leituras seguintes.</p>
      {valores && (
        <form className="painel" onSubmit={salvar}>
          {campos.map(([k, nome, max]) => (
            <label key={k}>
              {nome}
              <input type="number" min="0" max={max} value={valores[k]} onChange={(e) => setValores({ ...valores, [k]: e.target.value })} required />
            </label>
          ))}
          <button className="btn">Salvar parâmetros</button>
        </form>
      )}
      {status && <p role="status">{status}</p>}
    </>
  );
}
