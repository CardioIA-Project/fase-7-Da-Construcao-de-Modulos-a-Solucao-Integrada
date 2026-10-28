import sys

import requests

from app.config import Config
from app.services.watson import criar_cliente


def _config() -> dict:
    return {nome: getattr(Config, nome) for nome in dir(Config) if nome.startswith("WATSON_")}


def _falha(etapa: str, erro: Exception) -> int:
    print(f"FALHOU em: {etapa}")
    if isinstance(erro, requests.HTTPError) and erro.response is not None:
        print(f"  status HTTP: {erro.response.status_code}")
        print(f"  resposta: {erro.response.text[:300]}")
        if erro.response.status_code in (401, 403):
            print("  dica: confira WATSON_API_KEY e se a URL é a da mesma instância.")
        if erro.response.status_code == 404:
            print("  dica: confira WATSON_ASSISTANT_ID. Se a sua conta usa assistente e ambiente separados, preencha WATSON_ENVIRONMENT_ID.")
    else:
        print(f"  erro: {type(erro).__name__}: {erro}")
        print("  dica: confira WATSON_URL e a conexão com a internet.")
    return 1


def main(config: dict | None = None) -> int:
    cliente = criar_cliente(config or _config())
    if cliente is None:
        print("Faltam variáveis: WATSON_API_KEY, WATSON_URL e WATSON_ASSISTANT_ID.")
        return 1
    try:
        sessao = cliente.criar_sessao()
    except Exception as erro:
        return _falha("criar sessão", erro)
    print("OK  sessão criada")
    for texto in ("Tontura", "Leve", "Horas", "nenhum", "Dor no peito"):
        try:
            resposta = cliente.enviar(sessao, texto)
        except Exception as erro:
            return _falha(f"enviar mensagem {texto!r}", erro)
        print(f"OK  você: {texto!r}")
        for linha in resposta["replies"]:
            print(f"      watson: {linha}")
        if resposta["options"]:
            print(f"      opções: {resposta['options']}")
    try:
        cliente.encerrar(sessao)
        print("OK  sessão encerrada")
    except Exception as erro:
        return _falha("encerrar sessão", erro)
    print("Tudo certo: o Watson está respondendo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
