def limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def mapear(bruto, adc_max, minimo, maximo):
    bruto = limitar(bruto, 0, adc_max)
    return minimo + (maximo - minimo) * bruto / adc_max


def ler_media(leitor, amostras=8):
    total = 0
    for _ in range(amostras):
        total += leitor()
    return total / amostras


def montar_leitura(paciente_id, dispositivo, fc, spo2, temperatura):
    return {
        "paciente_id": paciente_id,
        "fc_media": round(limitar(fc, 20, 250), 1),
        "temperatura": round(limitar(temperatura, -20, 60), 1),
        "spo2_media": round(limitar(spo2, 0, 100), 1),
        "dispositivo": dispositivo,
    }


def pontos_de_risco(fc, spo2):
    pontos = 0
    if fc > 110:
        pontos += 1
    if spo2 < 92:
        pontos += 1
    return pontos


def classificar_local(fc, spo2):
    pontos = pontos_de_risco(fc, spo2)
    if pontos >= 2:
        return "ALTO"
    if pontos == 1:
        return "MODERADO"
    return "BAIXO"


def estado_leds(classificacao):
    return {
        "BAIXO": (1, 0, 0),
        "MODERADO": (0, 1, 0),
        "ALTO": (0, 0, 1),
    }.get(classificacao, (0, 0, 0))


def linhas_oled(leitura, classificacao, probabilidade, origem, status):
    linhas = [
        "CardioIA " + leitura["paciente_id"],
        "FC:%3d  SpO2:%3d" % (round(leitura["fc_media"]), round(leitura["spo2_media"])),
        "Temp: %.1f C" % leitura["temperatura"],
    ]
    if probabilidade is None:
        linhas.append("Risco: %s" % classificacao)
    else:
        linhas.append("Risco: %s %d%%" % (classificacao, round(probabilidade * 100)))
    linhas.append("%s | %s" % (origem, status))
    return linhas