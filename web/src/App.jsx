import { useEffect, useState } from "react";
import { api, salvarSessao, sessaoSalva } from "./api";
import Painel from "./Painel.jsx";
import Paciente from "./Paciente.jsx";
import Operacao from "./Operacao.jsx";
import Chat from "./Chat.jsx";

function Login({ onEntrar, onChat }) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [envio, setEnvio] = useState(false);

  const enviar = async (e) => {
    e.preventDefault();
    setErro("");
    setEnvio(true);
    try {
      const d = await api("/api/auth/login", { metodo: "POST", auth: false, corpo: { usuario, senha } });
      onEntrar({ token: d.token, perfil: d.perfil, paciente_id: d.paciente_id, nome: d.nome });
    } catch (err) {
      if (err.status === 0) setErro("Sem conexão com o servidor. Se ele estava inativo, aguarde cerca de um minuto e tente de novo.");
      else if ([401, 403, 422].includes(err.status)) setErro("Usuário ou senha incorretos.");
      else setErro("Não foi possível entrar. Tente de novo.");
    } finally {
      setEnvio(false);
    }
  };

  return (
    <main className="entrada">
      <h1>CardioIA</h1>
      <p className="suave">Monitoramento de risco cardíaco em tempo real.</p>
      <form className="painel" onSubmit={enviar}>
        <label>
          Usuário
          <input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username" required />
        </label>
        <label>
          Senha
          <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="current-password" required />
        </label>
        {erro && <p className="erro" role="alert">{erro}</p>}
        <button className="btn" disabled={envio}>{envio ? "Entrando" : "Entrar"}</button>
      </form>
      <button className="link" onClick={onChat}>Fazer triagem de sintomas sem entrar</button>
    </main>
  );
}

export default function App() {
  const [sessao, setSessao] = useState(sessaoSalva());
  const [aba, setAba] = useState("painel");
  const [pacienteId, setPacienteId] = useState(null);

  const sair = () => {
    salvarSessao(null);
    setSessao(null);
    setAba("painel");
    setPacienteId(null);
  };

  useEffect(() => {
    window.addEventListener("sessao-expirada", sair);
    return () => window.removeEventListener("sessao-expirada", sair);
  }, []);

  const entrar = (s) => {
    salvarSessao(s);
    setSessao(s);
    setAba("painel");
  };

  if (!sessao) {
    if (aba === "chat")
      return (
        <main>
          <button className="link" onClick={() => setAba("painel")}>Voltar ao login</button>
          <Chat />
        </main>
      );
    return <Login onEntrar={entrar} onChat={() => setAba("chat")} />;
  }

  const medico = sessao.perfil === "medico";
  const abas = medico
    ? [["painel", "Pacientes"], ["operacao", "Hospital"], ["chat", "Triagem"]]
    : [["painel", "Meu painel"], ["chat", "Triagem"]];

  const trocar = (a) => {
    setAba(a);
    setPacienteId(null);
  };

  return (
    <>
      <header className="topo">
        <div>
          <span className="marca">CardioIA</span>
          <nav className="abas">
            {abas.map(([id, nome]) => (
              <button key={id} aria-current={aba === id ? "page" : undefined} onClick={() => trocar(id)}>{nome}</button>
            ))}
          </nav>
          <span className="suave">{sessao.nome}</span>
          <button className="sair" onClick={sair}>Sair</button>
        </div>
      </header>
      <main>
        {aba === "painel" && medico && (pacienteId
          ? <Paciente id={pacienteId} onVoltar={() => setPacienteId(null)} />
          : <Painel onAbrir={setPacienteId} />)}
        {aba === "painel" && !medico && <Paciente id={null} />}
        {aba === "operacao" && medico && <Operacao />}
        {aba === "chat" && <Chat />}
      </main>
    </>
  );
}
