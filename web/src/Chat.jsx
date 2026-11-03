import { useEffect, useRef, useState } from "react";
import { api } from "./api";

export default function Chat() {
  const [sessao, setSessao] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [opcoes, setOpcoes] = useState([]);
  const [emergencia, setEmergencia] = useState(false);
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState("");
  const fim = useRef(null);

  const abrir = async () => {
    const d = await api("/api/session", { metodo: "POST", auth: false });
    setSessao(d.session_id);
    return d.session_id;
  };

  const aplicar = (d) => {
    setMsgs((m) => [...m, ...d.replies.map((t) => ({ de: "bot", t }))]);
    setOpcoes(d.options || []);
    setEmergencia(!!d.emergencia);
  };

  const enviar = async (t, silencioso = false) => {
    const msg = t.trim();
    if (!msg) return;
    setErro("");
    setTexto("");
    setOpcoes([]);
    if (!silencioso) setMsgs((m) => [...m, { de: "eu", t: msg }]);
    const chamar = (id) => api("/api/message", { metodo: "POST", auth: false, corpo: { session_id: id, text: msg } });
    try {
      const id = sessao || (await abrir());
      try {
        aplicar(await chamar(id));
      } catch (e) {
        if (e.status !== 404) throw e;
        aplicar(await chamar(await abrir()));
      }
    } catch {
      setErro("Não foi possível falar com o servidor. Tente de novo.");
    }
  };

  const reiniciar = async () => {
    if (sessao) api(`/api/session/${sessao}`, { metodo: "DELETE", auth: false }).catch(() => {});
    setSessao(null);
    setMsgs([]);
    setEmergencia(false);
    setTimeout(() => enviar("oi", true), 0);
  };

  useEffect(() => {
    enviar("oi", true);
  }, []);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [msgs, opcoes]);

  return (
    <>
      <h1>Triagem de sintomas</h1>
      {emergencia && (
        <div className="emerg" role="alert">
          <strong>Possível emergência. Procure atendimento agora.</strong>
          <br />
          <a href="tel:192">Ligar para o 192</a>
        </div>
      )}
      <div className="painel chat">
        <div className="conversa" aria-live="polite">
          {msgs.map((m, i) => <p key={i} className={`bolha ${m.de}`}>{m.t}</p>)}
          {opcoes.length > 0 && (
            <div className="opcoes">
              {opcoes.map((o) => <button key={o} onClick={() => enviar(o)}>{o}</button>)}
            </div>
          )}
          <div ref={fim} />
        </div>
        {erro && <p className="erro" role="alert">{erro}</p>}
        <form className="envio" onSubmit={(e) => { e.preventDefault(); enviar(texto); }}>
          <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Descreva o que você sente" disabled={emergencia} aria-label="Sua mensagem" />
          <button className="btn" disabled={emergencia || !texto.trim()}>Enviar</button>
        </form>
      </div>
      <button className="link" onClick={reiniciar}>Começar nova triagem</button>
      <p className="suave"><small>Protótipo acadêmico. Não substitui avaliação médica.</small></p>
    </>
  );
}
