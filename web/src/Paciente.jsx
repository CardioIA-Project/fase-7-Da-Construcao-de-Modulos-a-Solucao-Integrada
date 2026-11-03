import { api, usePolling } from "./api";
import { hora, rotulo } from "./Painel.jsx";

function Grafico({ pontos }) {
  if (pontos.length < 2) return <p className="vazio">O gráfico aparece após duas leituras.</p>;
  const w = 600;
  const h = 140;
  const x = (i) => (i / (pontos.length - 1)) * w;
  const y = (p) => h - Math.min(Math.max(p, 0), 1) * h;
  const linha = pontos.map((p, i) => `${x(i).toFixed(1)},${y(p).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="grafico" role="img" aria-label="Probabilidade de crise ao longo do tempo">
      <line x1="0" x2={w} y1={y(0.7)} y2={y(0.7)} className="ref alto" />
      <line x1="0" x2={w} y1={y(0.3)} y2={y(0.3)} className="ref moderado" />
      <polyline points={linha} className="traco" />
    </svg>
  );
}

export default function Paciente({ id, onVoltar }) {
  const qs = id ? `?paciente_id=${encodeURIComponent(id)}` : "";
  const ultimo = usePolling(() => api(`/api/sinais/ultimo${qs}`), 3000, [id]);
  const hist = usePolling(() => api(`/api/sinais/historico${qs}${qs ? "&" : "?"}limite=60`), 3000, [id]);

  const lista = Array.isArray(hist.dados) ? hist.dados : hist.dados?.leituras || hist.dados?.historico || hist.dados?.itens || [];
  const pontos = lista.map((i) => i.probabilidade_crise).filter(Number.isFinite);
  const d = ultimo.dados;
  const s = d?.sinais;

  return (
    <>
      {onVoltar && <button className="link" onClick={onVoltar}>Voltar à lista</button>}
      {ultimo.carregando && <p className="suave">Carregando leitura</p>}
      {!ultimo.carregando && ultimo.erro?.status === 404 && (
        <p className="vazio">Este paciente ainda não tem leituras. Assim que o sensor enviar dados, eles aparecem aqui.</p>
      )}
      {ultimo.erro && ultimo.erro.status !== 404 && !d && (
        <p className="erro" role="alert">Não foi possível carregar a leitura. Verifique a conexão.</p>
      )}
      {d && (
        <>
          <section className={`faixa ${d.classificacao.toLowerCase()}`} aria-live="polite">
            <h1>Risco {rotulo[d.classificacao].toLowerCase()}</h1>
            <p>
              Probabilidade de crise: <strong>{Math.round(d.probabilidade_crise * 100)}%</strong>. Paciente {d.paciente_id}, leitura de {hora(d.timestamp)}.
            </p>
            <div className="barra"><i style={{ width: `${d.probabilidade_crise * 100}%` }} /></div>
          </section>

          <h2>Recomendação</h2>
          <p>{d.recomendacao}</p>

          <h2>Sinais da última leitura</h2>
          <dl className="sinais">
            <div><dt>Frequência cardíaca</dt><dd>{s.fc_media} bpm</dd></div>
            <div><dt>Saturação (SpO2)</dt><dd>{s.spo2_media} %</dd></div>
            <div><dt>Temperatura</dt><dd>{s.temperatura} °C</dd></div>
            <div><dt>Pressão sistólica</dt><dd>{s.pa_sistolica} mmHg</dd></div>
            <div><dt>Eventos em 24 h</dt><dd>{s.eventos_24h}</dd></div>
          </dl>

          <h2>O que pesou no risco</h2>
          {d.fatores.length ? <ul>{d.fatores.map((f) => <li key={f}>{f}</li>)}</ul> : <p className="suave">Nenhum fator de alerta.</p>}

          <h2>Protocolos acionados</h2>
          {d.protocolos.length ? (
            <ul>{d.protocolos.map((p) => <li key={p.id}><strong>{p.texto}.</strong> {p.acao}</li>)}</ul>
          ) : (
            <p className="suave">Nenhum protocolo acionado.</p>
          )}

          <h2>Probabilidade ao longo do tempo</h2>
          <Grafico pontos={pontos} />
          <p className="suave"><small>Linha vermelha: limite de risco alto (70%). Linha amarela: risco moderado (30%).</small></p>
          <p className="suave"><small>{d.aviso}</small></p>
        </>
      )}
    </>
  );
}
