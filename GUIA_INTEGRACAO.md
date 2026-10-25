# Guia de Integração — CardioIA Backend

Para quem vai construir o front web, o app mobile e o sensor (Wokwi). Tudo aqui foi gerado a partir do backend rodando.

## 1. O que você precisa do dono do backend

| Item | Onde usar |
| :--- | :--- |
| `URL_BASE` (ex.: `https://cardioia-api.onrender.com`) | Web, mobile e sensor |
| `DEVICE_API_KEY` | Só o sensor (Wokwi), no header `X-Device-Key` |
| Usuários de login (`medico` e `paciente`) e senhas | Web e mobile |

Nunca coloquem a `DEVICE_API_KEY` no front web ou no app. Ela é só do sensor.

## 2. Como as interfaces falam com o backend

```text
Sensor (Wokwi)  --POST /api/sinais + X-Device-Key-->  Backend  -->  modelo + protocolos  -->  SQLite
Web / Mobile    --POST /api/auth/login-->  token
Web / Mobile    --GET /api/sinais/ultimo + Bearer token (a cada 3 s)-->  última leitura e recomendação
Web / Mobile    --POST /api/session e /api/message-->  triagem conversacional
```

Tempo real é por polling: a tela repete `GET /api/sinais/ultimo` a cada poucos segundos.

## 3. Autenticação

**Médico e paciente:** `POST /api/auth/login` devolve um token. Enviem `Authorization: Bearer <token>` nas demais rotas. O token vale 12 horas.

```bash
curl -X POST $URL_BASE/api/auth/login -H "Content-Type: application/json" -d '{"usuario":"medico","senha":"medico123"}'
```

```json
{
  "nome": "Dra. Demo",
  "paciente_id": null,
  "perfil": "medico",
  "token": "<token>",
  "usuario": "medico"
}
```

- `perfil: "paciente"` só enxerga o próprio `paciente_id`. Pedir outro paciente retorna 403.
- `perfil: "medico"` enxerga todos e pode alterar `/api/operacao`.
- Credenciais de demonstração: `medico` / `medico123` e `paciente` / `paciente123`, se o dono do backend não tiver trocado.

```javascript
const resposta = await fetch(`${URL_BASE}/api/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ usuario, senha }),
});
const { token, perfil, paciente_id } = await resposta.json();

const ultimo = await fetch(`${URL_BASE}/api/sinais/ultimo?paciente_id=p001`, {
  headers: { Authorization: `Bearer ${token}` },
});
```

Para o paciente, omitam o `paciente_id`: o backend usa o do token.

## 4. Endpoints

| Método | Rota | Quem | Para que |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | qualquer | Verificar se está no ar |
| `POST` | `/api/auth/login` | qualquer | Obter token |
| `GET` | `/api/auth/me` | login | Identidade do token |
| `POST` | `/api/sinais` | sensor | Enviar leitura |
| `GET` | `/api/sinais/ultimo?paciente_id=` | login | Última leitura e recomendação |
| `GET` | `/api/sinais/historico?paciente_id=&limite=` | login | Série para gráfico (até 500, ordem cronológica) |
| `GET` | `/api/pacientes` | médico | Lista com último risco de cada paciente |
| `POST` | `/api/risco` | login | Risco a partir das 10 variáveis completas |
| `POST` | `/api/analise` | login | Reanálise da última leitura (`{"paciente_id": "p001"}`) |
| `GET` / `PUT` | `/api/operacao` | médico | Ler e alterar parâmetros do hospital |
| `POST` | `/api/session` | qualquer | Abrir triagem |
| `POST` | `/api/message` | qualquer | Enviar mensagem na triagem |
| `DELETE` | `/api/session/<id>` | qualquer | Encerrar triagem |

### Leitura do sensor

```bash
curl -X POST $URL_BASE/api/sinais -H "Content-Type: application/json" -H "X-Device-Key: $DEVICE_API_KEY" -d '{"paciente_id":"p001","fc_media":130,"temperatura":24,"spo2_media":85,"dispositivo":"esp32-wokwi"}'
```

Campos: `paciente_id` (letras, números, `_` e `-`, até 40), `fc_media` (20 a 250), `temperatura` (-20 a 60), e opcionais `spo2_media` (0 a 100), `pa_sistolica` (40 a 300) e `dispositivo`. Qualquer campo a mais retorna 422.

Resposta `201` (a mesma estrutura sai em `GET /api/sinais/ultimo`):

```json
{
  "aviso": "Protótipo acadêmico com dados sintéticos. Não substitui avaliação médica.",
  "classificacao": "ALTO",
  "dispositivo": "esp32-wokwi",
  "fatores": ["SpO2 abaixo de 92%", "Frequência cardíaca acima de 110 bpm"],
  "id": 1,
  "origem": "deterministico",
  "paciente_id": "p001",
  "probabilidade_crise": 0.825,
  "protocolos": [
    {
      "acao": "Colocar o paciente em monitoramento intensivo de frequência cardíaca.",
      "id": "fc_alta",
      "texto": "Se FC > 120 → iniciar monitoramento intensivo"
    }
  ],
  "recomendacao": "Risco ALTO de pico de crise (82%). Acionar a equipe médica imediatamente. Ações: ...",
  "sinais": {
    "eventos_24h": 0.0,
    "fc_media": 130.0,
    "pa_sistolica": 125.0,
    "spo2_media": 85.0,
    "temperatura": 24.0
  },
  "timestamp": "2026-10-24T00:30:11.199978+00:00"
}
```

- `classificacao` é `BAIXO`, `MODERADO` ou `ALTO`. Usem para cor e destaque: verde, amarelo e vermelho.
- `probabilidade_crise` vai de 0 a 1.
- `protocolos` pode vir vazio. `fatores` lista o que pesou no risco.
- `timestamp` está em UTC. Convertam para o horário local ao exibir.
- Se o paciente ainda não tem leitura, `GET /api/sinais/ultimo` retorna 404 com `{"erro":"sem_leituras"}`. Mostrem um estado vazio, não um erro.

### Lista de pacientes (médico)

```json
{
  "pacientes": [
    {
      "id": "p001",
      "idade": 55.0,
      "nome": "Paciente p001",
      "ultima_atualizacao": "2026-10-24T00:30:11.199978+00:00",
      "ultima_classificacao": "ALTO",
      "ultima_probabilidade": 0.825
    }
  ],
  "solicitante": "medico"
}
```

### Parâmetros operacionais (médico)

`GET /api/operacao` devolve `carga_sistema`, `tempo_espera`, `disponibilidade_recursos` e `densidade_eventos`. `PUT /api/operacao` aceita qualquer subconjunto (carga e recursos de 0 a 100, espera até 1440, densidade até 100). Esses valores entram no cálculo do risco de todas as leituras seguintes, então servem para uma tela de "situação do hospital".

## 5. Triagem conversacional (chat)

```bash
curl -X POST $URL_BASE/api/session
curl -X POST $URL_BASE/api/message -H "Content-Type: application/json" -d '{"session_id":"<id>","text":"oi"}'
```

Resposta:

```json
{
  "emergencia": false,
  "finalizado": false,
  "origem": "local",
  "options": ["Dor no peito", "Falta de ar", "Palpitação", "Tontura", "Cansaço", "Inchaço nas pernas", "Dor no braço", "Suor frio"],
  "replies": [
    "Bem-vindo, como posso ajudá-lo?",
    "Entendi. Esse assistente faz uma triagem inicial e não substitui uma avaliação médica. Qual sintoma você está sentindo?"
  ]
}
```

- Mostrem cada item de `replies` como uma bolha.
- Se `options` não estiver vazio, mostrem botões. Ao tocar, enviem o texto do botão em `text`. O usuário também pode digitar.
- `emergencia: true` deve ganhar destaque visual forte (vermelho, botão para ligar 192). O fluxo termina ali.
- `origem` é `"watson"` ou `"local"` e diz quem gerou a resposta. Não precisa ser exibido, mas ajuda a depurar e a explicar a arquitetura no vídeo.
- `finalizado: true` indica o fim. Uma nova mensagem na mesma sessão reinicia a triagem.
- Sessão expirada ou inexistente retorna 404. Abram outra com `POST /api/session`.

`GET /api/triagem/status` (sem login) mostra se o Watson está configurado e ativo: `{"watson_configurado": true, "watson_ativo": true, "reserva_local": true}`. Se o Watson cair, o backend usa a triagem local sozinho, sem mudar o contrato. Perguntas de emergência ("dor no peito" etc.) são sempre decididas localmente, antes do Watson.

**Diferenças em relação ao app da Fase 5:**
1. `POST /api/session` responde **201**. Se o app testa `status === 200`, troquem por `res.ok`.
2. As opções vêm no campo `options` e **não** vêm dentro de `replies`. Se o app da Fase 5 mostrava o menu como texto em `replies`, agora é preciso renderizar `options`, senão o usuário não vê o menu.
3. O corpo da requisição é o mesmo: `{ "session_id": "...", "text": "..." }`.

## 6. Erros

Todos os erros vêm em JSON.

| Código | Quando | Corpo |
| :--- | :--- | :--- |
| 400 | Corpo não é um objeto JSON, ou chat sem `session_id`/`text` | `{"erro": "requisicao_invalida"}` |
| 401 | Sem token, token inválido ou expirado, chave do sensor errada | `{"erro": "nao_autenticado"}` ou `{"erro": "dispositivo_nao_autorizado"}` |
| 403 | Perfil sem permissão | `{"erro": "acesso_negado"}` |
| 404 | Sem leituras, sessão inexistente ou rota errada | `{"erro": "sem_leituras"}` etc. |
| 413 | Corpo acima de 64 KB | `{"erro": "corpo_muito_grande"}` |
| 422 | Campo ausente, extra ou fora da faixa | `{"erro": "validacao", "detalhes": [{"loc": ["fc_media"], "msg": "...", "type": "..."}]}` |
| 500 | Falha inesperada | `{"erro": "erro_interno"}` |

Em 401 no front, voltem para a tela de login.

## 7. CORS

O backend aceita qualquer origem por padrão (`CORS_ORIGINS=*`), então web (Vercel), Expo e navegador funcionam sem ajuste. Para restringir, definam `CORS_ORIGINS` com as URLs separadas por vírgula.

## 8. Deploy do backend no Render

O dono do backend faz uma vez só.

1. Subam o monorepo para o GitHub.
2. No Render: **New → Web Service**, escolham o repositório.
3. Configurem:

| Campo | Valor |
| :--- | :--- |
| Root Directory | `backend` |
| Runtime | Python |
| Build Command | `pip install -r requirements.txt && python treinar_modelo.py` |
| Start Command | `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 60` |
| Health Check Path | `/health` |

4. Em **Environment**, definam:

| Variável | Valor |
| :--- | :--- |
| `PYTHON_VERSION` | `3.12.7` |
| `SECRET_KEY` | texto aleatório longo |
| `DEVICE_API_KEY` | texto aleatório (vai para o Wokwi) |
| `MEDICO_SENHA` | senha do médico |
| `PACIENTE_SENHA` | senha do paciente |
| `WATSON_API_KEY`, `WATSON_URL`, `WATSON_ASSISTANT_ID` | Opcionais. Credenciais do Watson Assistant. Sem elas, só a triagem local é usada |
| `WATSON_ENVIRONMENT_ID` | Opcional. Só se a sua instância exigir assistente e ambiente separados |

5. Testem: `curl $URL_BASE/health` deve devolver `{"status":"ok"}`.

O `render.yaml` automatiza isso, mas o Render só o lê na **raiz** do repositório. Se quiserem usá-lo, copiem-no do `backend/` para a raiz do monorepo (ele já aponta `rootDir: backend`).

Use **1 worker**: as sessões do chat ficam em memória.

### Plano gratuito

- O serviço hiberna depois de um tempo sem uso, e a primeira requisição pode levar cerca de um minuto. Confiram os detalhes atuais na documentação do Render.
- O disco é efêmero: o histórico zera a cada reinício, e o backend recria um histórico de exemplo para o paciente `p001` (`SEED_DEMO=true`).
- Antes de gravar o vídeo, acordem o serviço com `curl $URL_BASE/health`.

## 8.1 Conectar o Watson (opcional)

1. Quem tem a conta ativa da IBM importa `watson/Assistente-Cardiológico-Conversacional-action.json` no watsonx Assistant e confirma no preview que "dor no peito" aciona a emergência.
2. Em **Environments → Draft → API details**, copia a URL, o ID e a API key (**Service credentials**).
3. Roda o diagnóstico na própria máquina, antes de mexer no Render:

```bash
cd backend
cp .env.example .env
python testar_watson.py
```

Preencha `WATSON_API_KEY`, `WATSON_URL` e `WATSON_ASSISTANT_ID` no `.env` (o arquivo não vai para o GitHub). O script cria uma sessão, percorre o fluxo inteiro e mostra o que o Watson respondeu. Se algo falhar, ele indica a etapa e uma dica.

4. Com `Tudo certo` no script, colocar as mesmas variáveis no Render. `GET /api/triagem/status` deve mostrar `"watson_ativo": true`.

Observações:
- Se o diagnóstico der 404, tentem preencher `WATSON_ENVIRONMENT_ID` com o ID do ambiente (Draft ou Live).
- O texto do resumo final da Action começa com uma aspa solta (`"Resumindo...`) e tem `,há` sem espaço. Corrijam na Action, no passo 6.
- Nunca coloquem a API key no GitHub.

## 9. Roteiro para a demonstração

1. Login como `medico` na web ou no app e abertura da tela do paciente `p001`.
2. No Wokwi, FC e SpO2 em valores normais (por exemplo, FC 72 e SpO2 97): risco **BAIXO**.
3. Girar o potenciômetro de FC acima de 110: sozinho dá **MODERADO**, não ALTO.
4. Girar também o de SpO2 abaixo de 92: o risco vai a **ALTO** e a tela atualiza no próximo polling.

O modelo foi treinado para exigir pelo menos 2 dos 6 critérios (FC > 110, SpO2 < 92, carga > 80, espera > 60, eventos > 4, recursos < 40) para chegar a ALTO. Com só o sensor, os dois critérios que ele controla são FC e SpO2.

## 10. Checklist antes de entregar

- [ ] `URL_BASE` do Render configurada no web, no mobile e no Wokwi (como variável de ambiente, nada fixo no código).
- [ ] `DEVICE_API_KEY` só no Wokwi.
- [ ] Login testado no `.apk` em um aparelho real.
- [ ] Tela tratando 404 de `/api/sinais/ultimo` (paciente sem leitura) e 401 (sessão expirada).
- [ ] Backend acordado antes da gravação.
