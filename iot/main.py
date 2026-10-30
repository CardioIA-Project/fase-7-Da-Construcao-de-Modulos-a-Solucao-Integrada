import time

import dht
import network
from machine import ADC, I2C, PWM, Pin

try:
    import urequests as requests
except ImportError:
    import requests

import config
import logica
from ssd1306 import SSD1306_I2C

sensor_dht = dht.DHT22(Pin(config.PINO_DHT))

adc_fc = ADC(Pin(config.PINO_FC))
adc_fc.atten(ADC.ATTN_11DB)
adc_spo2 = ADC(Pin(config.PINO_SPO2))
adc_spo2.atten(ADC.ATTN_11DB)

led_verde = Pin(config.PINO_LED_VERDE, Pin.OUT)
led_amarelo = Pin(config.PINO_LED_AMARELO, Pin.OUT)
led_vermelho = Pin(config.PINO_LED_VERMELHO, Pin.OUT)
buzzer = PWM(Pin(config.PINO_BUZZER), freq=config.BUZZER_HZ, duty=0)

i2c = I2C(0, sda=Pin(config.PINO_SDA), scl=Pin(config.PINO_SCL), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

ultima_temperatura = 24.0


def mostrar(linhas):
    oled.fill(0)
    for indice, texto in enumerate(linhas[:6]):
        oled.text(texto[:16], 0, indice * 10)
    oled.show()


def acender(classificacao):
    verde, amarelo, vermelho = logica.estado_leds(classificacao)
    led_verde.value(verde)
    led_amarelo.value(amarelo)
    led_vermelho.value(vermelho)
    buzzer.duty(0)
    if classificacao == "ALTO":
        for _ in range(config.BIPES):
            buzzer.duty(config.BUZZER_DUTY)
            time.sleep(config.BIPE_S)
            buzzer.duty(0)
            time.sleep(config.BIPE_S)


def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        mostrar(["CardioIA", "Conectando WiFi..."])
        wlan.connect(config.WIFI_SSID, config.WIFI_SENHA)
        for _ in range(40):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    return wlan


def ler_temperatura():
    global ultima_temperatura
    try:
        sensor_dht.measure()
        ultima_temperatura = sensor_dht.temperature()
    except OSError:
        pass
    return ultima_temperatura


def ler_sinais():
    fc = logica.mapear(
        logica.ler_media(adc_fc.read), config.ADC_MAX, config.FC_MIN, config.FC_MAX
    )
    spo2 = logica.mapear(
        logica.ler_media(adc_spo2.read), config.ADC_MAX, config.SPO2_MIN, config.SPO2_MAX
    )
    return fc, spo2, ler_temperatura()


def postar(leitura):
    url = config.API_URL + "/api/sinais"
    cabecalhos = {"X-Device-Key": config.DEVICE_KEY}
    try:
        return requests.post(url, json=leitura, headers=cabecalhos, timeout=config.TIMEOUT_S)
    except TypeError:
        return requests.post(url, json=leitura, headers=cabecalhos)


def enviar(leitura):
    for tentativa in range(config.TENTATIVAS_ENVIO):
        resposta = None
        try:
            resposta = postar(leitura)
            if resposta.status_code == 201:
                return resposta.json(), "HTTP 201"
            return None, "HTTP %d" % resposta.status_code
        except Exception as erro:
            print("erro de envio", tentativa + 1, repr(erro))
        finally:
            if resposta is not None:
                resposta.close()
    return None, "sem rede"


def ciclo(wlan):
    fc, spo2, temperatura = ler_sinais()
    leitura = logica.montar_leitura(
        config.PACIENTE_ID, config.DISPOSITIVO, fc, spo2, temperatura
    )
    resultado, status = (None, "sem wifi")
    if wlan.isconnected():
        resultado, status = enviar(leitura)
    if resultado is not None:
        classificacao = resultado["classificacao"]
        probabilidade = resultado["probabilidade_crise"]
        origem = "API"
    else:
        classificacao = logica.classificar_local(leitura["fc_media"], leitura["spo2_media"])
        probabilidade = None
        origem = "LOCAL"
    acender(classificacao)
    mostrar(logica.linhas_oled(leitura, classificacao, probabilidade, origem, status))
    print(origem, status, leitura, classificacao, probabilidade)


def principal():
    wlan = conectar_wifi()
    while True:
        if not wlan.isconnected():
            wlan = conectar_wifi()
        ciclo(wlan)
        time.sleep(config.INTERVALO_S)


principal()