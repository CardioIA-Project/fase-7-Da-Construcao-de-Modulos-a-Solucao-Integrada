# CardioIA — Backend Integrador (Fase 7)

API em Flask que conecta sensor (MicroPython), modelo preditivo (Random Forest da Fase 6), motor de protocolos clínicos, triagem conversacional (fluxo da Fase 5 portado para regras) e as interfaces Web e Mobile.

> Protótipo acadêmico com dados sintéticos. Não substitui avaliação médica.

## Executar localmente

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python treinar_modelo.py
python run.py
pytest
```

O servidor sobe em `http://localhost:5000`. Se o `.pkl` não existir, o backend treina o modelo na primeira inicialização.

## Autenticação

| Quem | Como | Credenciais de demonstração |
| :--- | :--- | :--- |
| Médico | `Authorization: Bearer <token>` | `medico` / `medico123` |
| Paciente | `Authorization: Bearer <token>` | `paciente` / `paciente123` |
| Sensor (ESP32) | Header `X-Device-Key` | valor de `DEVICE_API_KEY` |

Em produção, troque as senhas e a chave pelas variáveis de ambiente `MEDICO_SENHA`, `PACIENTE_SENHA` e `DEVICE_API_KEY`.

## Endpoints

| Método | Rota | Acesso | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | público | Healthcheck |
| `POST` | `/api/auth/login` | público | Corpo `{usuario, senha}`, retorna `token`, `perfil`, `paciente_id` |
| `GET` | `/api/auth/me` | login | Identidade do token |
| `POST` | `/api/sinais` | sensor | Recebe leitura, calcula risco e grava |
| `GET` | `/api/sinais/ultimo` | login | Última leitura e recomendação (`?paciente_id=`) |
| `GET` | `/api/sinais/historico` | login | Histórico (`?paciente_id=&limite=`) |
| `POST` | `/api/risco` | login | Risco a partir das 10 variáveis completas |
| `POST` | `/api/analise` | login | Reanálise da última leitura do paciente |
| `GET` | `/api/pacientes` | médico | Lista de pacientes com último status |
| `GET` / `PUT` | `/api/operacao` | médico | Parâmetros operacionais do hospital |
| `POST` | `/api/session` | público | Abre sessão de triagem |
| `POST` | `/api/message` | público | Corpo `{session_id, text}`, retorna `replies`, `options`, `emergencia`, `finalizado` |
| `DELETE` | `/api/session/<id>` | público | Encerra a sessão |

Pacientes só acessam os próprios dados. Valores fora das faixas válidas retornam `422`.

### Payload do sensor

```json
{
  "paciente_id": "p001",
  "fc_media": 130,
  "temperatura": 24,
  "spo2_media": 85,
  "pa_sistolica": 120,
  "dispositivo": "esp32-wokwi"
}
```

`spo2_media`, `pa_sistolica` e `dispositivo` são opcionais. Limites: `fc_media` 20–250, `temperatura` −20–60, `spo2_media` 0–100, `pa_sistolica` 40–300.

### Como o backend monta as 10 variáveis do modelo

| Variável | Origem |
| :--- | :--- |
| `fc_media`, `temperatura`, `spo2_media`, `pa_sistolica` | Sensor (SpO2 padrão 96 e PA padrão 125 se ausentes) |
| `idade_media` | Cadastro do paciente |
| `eventos_24h` | Episódios de risco ALTO do paciente nas últimas 24h (transições para ALTO, não leituras) |
| `carga_sistema`, `tempo_espera`, `disponibilidade_recursos`, `densidade_eventos` | Parâmetros operacionais (`/api/operacao`) |

O rótulo de treino exige pelo menos 2 de 6 critérios: carga > 80, espera > 60, SpO2 < 92, FC > 110, eventos > 4 e recursos < 40. Por isso uma leitura com só FC alta ou só SpO2 baixa fica abaixo de ALTO, e as duas juntas passam. `pa_sistolica`, `temperatura` e `idade_media` não influenciam o rótulo.

## Deploy no Render

O `render.yaml` define build (`pip install` e treino do modelo), start com gunicorn (1 worker e 4 threads, porque a triagem guarda sessões em memória) e healthcheck. Defina `MEDICO_SENHA` e `PACIENTE_SENHA` no painel. No plano gratuito o serviço hiberna sem uso e o disco é efêmero, então o SQLite é recriado com dados de demonstração a cada reinício (`SEED_DEMO=true`).

## Testes e robustez

`pytest` roda 88 testes: fluxo sensor → risco → histórico, permissões por perfil, validação de entradas (corpos que não são objeto JSON, `NaN`/infinito, valores fora da faixa, `paciente_id` inválido, corpo gigante), token adulterado e expirado, CORS, erros inesperados em JSON e a triagem com frases de emergência variadas. Toda falha encontrada em auditoria virou teste de regressão.

Verificado em instalação limpa (Python 3.12, só `requirements.txt`): build com treino do modelo em cerca de 3 s, servidor saudável em 1 a 3 s, 120 leituras e 40 conversas concorrentes sem erro, e dados preservados após reiniciar.

## Limitações conhecidas

- A triagem reconhece sintomas por palavras e padrões, sem NLP. Frases fora do vocabulário (por exemplo "quase desmaiei") caem no menu de opções em vez de acionar a emergência.
- Negações não são interpretadas: "não tenho dor no peito" aciona a emergência. É uma escolha deliberada pelo lado seguro.
- As sessões do chat ficam em memória (limite de 2000, expiram em 1 hora) e se perdem ao reiniciar o servidor.
- O modelo reproduz uma regra sintética do treino. O resultado é um protótipo acadêmico, sem valor clínico.

