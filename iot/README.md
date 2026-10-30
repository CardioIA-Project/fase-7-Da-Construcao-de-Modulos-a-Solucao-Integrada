# CardioIA — IoT (MicroPython no Wokwi)

Simulação de um ESP32 que lê os sinais do paciente, envia para o backend e mostra o risco devolvido em LEDs, buzzer e display OLED. Se a rede ou o backend falharem, o dispositivo classifica localmente e continua dando feedback.

## Hardware simulado

| Componente | Pino | Papel |
| :--- | :--- | :--- |
| DHT22 | GPIO 15 | Temperatura |
| Potenciômetro 1 | GPIO 34 | Frequência cardíaca (40 a 180 bpm) |
| Potenciômetro 2 | GPIO 35 | SpO2 (80 a 100%) |
| OLED SSD1306 (I2C) | GPIO 21 (SDA), 22 (SCL) | Sinais, risco e origem da classificação |
| LED verde / amarelo / vermelho | GPIO 25 / 26 / 27 | Risco BAIXO / MODERADO / ALTO |
| Buzzer | GPIO 14 (PWM, 2 kHz) | Alarme quando o risco é ALTO |

## Arquivos

| Arquivo | Função |
| :--- | :--- |
| `main.py` | Laço principal: leitura, envio, feedback visual |
| `logica.py` | Funções puras (mapeamento do ADC, limites, classificação local, textos do OLED) |
| `config.py` | URL do backend, chave do dispositivo, pinos e faixas |
| `ssd1306.py` | Driver do OLED (biblioteca oficial do MicroPython) |
| `diagram.json` | Circuito do Wokwi |
| `tests/` | Testes em Python comum (`pytest`) |

## Rodar no Wokwi

1. Em wokwi.com, crie um projeto **MicroPython no ESP32**.
2. Copie `main.py`, `logica.py`, `config.py`, `ssd1306.py` e `diagram.json` para o projeto.
3. Em `config.py`, troque `API_URL` pela URL pública do backend e `DEVICE_KEY` pelo valor de `DEVICE_API_KEY` configurado no Render.
4. Dê play. O ESP32 conecta na rede `Wokwi-GUEST` e envia uma leitura a cada 3 segundos.
5. Gire os potenciômetros: FC acima de 110 e SpO2 abaixo de 92 levam o risco a ALTO.

## Se algo não funcionar

| Sintoma no OLED ou no monitor serial | Causa provável |
| :--- | :--- |
| `LOCAL` e `sem rede` | O servidor do Render estava dormindo (a primeira chamada pode levar cerca de 1 minuto) ou a URL está errada. Abra `URL/health` no navegador e espere responder. As leituras seguintes voltam a usar a API |
| `HTTP 401` | `DEVICE_KEY` diferente do `DEVICE_API_KEY` configurado no Render |
| `HTTP 422` | Valor fora da faixa válida |
| `HTTP 301` | A URL está com `http://`. Use `https://` |
| `LOCAL` e `sem wifi` | Mantenha a rede `Wokwi-GUEST` e dê alguns segundos para conectar |

## Payload enviado

`POST /api/sinais` com o header `X-Device-Key`:

```json
{
  "paciente_id": "p001",
  "fc_media": 130.0,
  "temperatura": 24.0,
  "spo2_media": 85.0,
  "dispositivo": "esp32-wokwi"
}
```

O backend responde `201` com `classificacao`, `probabilidade_crise`, `protocolos` e `recomendacao`. O OLED mostra a origem da classificação: `API` (modelo do backend) ou `LOCAL` (regra de borda).

## Classificação local (fallback)

Espelha os dois critérios do rótulo de treino que o sensor controla: FC acima de 110 e SpO2 abaixo de 92. Um critério vale MODERADO e os dois valem ALTO. A classificação oficial é a do modelo no backend.

## Testes

```bash
cd iot
pip install pytest
pytest tests
```

Os testes cobrem a lógica pura e rodam `main.py` com módulos simulados, ligados ao backend Flask real. Eles não substituem a execução no Wokwi.
