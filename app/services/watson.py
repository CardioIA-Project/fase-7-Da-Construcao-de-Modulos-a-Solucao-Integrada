from __future__ import annotations

import threading
import time

import requests

IAM_PADRAO = "https://iam.cloud.ibm.com/identity/token"


def extrair_resposta(resposta: dict) -> dict:
    textos: list[str] = []
    opcoes: list[str] = []
    for item in resposta.get("output", {}).get("generic", []):
        tipo = item.get("response_type")
        if tipo == "text":
            texto = (item.get("text") or "").strip()
            if texto:
                textos.append(texto)
        elif tipo == "option":
            titulo = (item.get("title") or "").strip()
            if titulo:
                textos.append(titulo)
            for opcao in item.get("options", []):
                rotulo = (opcao.get("label") or "").strip()
                if rotulo:
                    opcoes.append(rotulo)
    return {"replies": textos, "options": opcoes}


class WatsonClient:
    def __init__(
        self,
        api_key: str,
        url: str,
        assistant_id: str,
        version: str,
        timeout: float,
        environment_id: str | None = None,
        iam_url: str = IAM_PADRAO,
    ) -> None:
        self._api_key = api_key
        self._url = url.rstrip("/")
        self._assistant_id = assistant_id
        self._environment_id = environment_id or None
        self._version = version
        self._timeout = timeout
        self._iam_url = iam_url
        self._http = requests.Session()
        self._token: str | None = None
        self._expira = 0.0
        self._trava = threading.Lock()

    def _base(self) -> str:
        if self._environment_id:
            return f"{self._url}/v2/assistants/{self._assistant_id}/environments/{self._environment_id}"
        return f"{self._url}/v2/assistants/{self._assistant_id}"

    def _obter_token(self, forcar: bool = False) -> str:
        with self._trava:
            if not forcar and self._token and time.monotonic() < self._expira:
                return self._token
            resposta = self._http.post(
                self._iam_url,
                data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": self._api_key},
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            )
            resposta.raise_for_status()
            dados = resposta.json()
            self._token = dados["access_token"]
            self._expira = time.monotonic() + max(int(dados.get("expires_in", 3600)) - 60, 0)
            return self._token

    def _requisitar(self, metodo: str, caminho: str, corpo: dict | None = None) -> dict:
        for tentativa in (0, 1):
            token = self._obter_token(forcar=tentativa == 1)
            resposta = self._http.request(
                metodo,
                self._base() + caminho,
                params={"version": self._version},
                json=corpo,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=self._timeout,
            )
            if resposta.status_code == 401 and tentativa == 0:
                continue
            resposta.raise_for_status()
            return resposta.json() if resposta.content else {}
        return {}

    def criar_sessao(self) -> str:
        return self._requisitar("POST", "/sessions")["session_id"]

    def enviar(self, sessao_id: str, texto: str) -> dict:
        corpo = {"input": {"message_type": "text", "text": texto}}
        return extrair_resposta(self._requisitar("POST", f"/sessions/{sessao_id}/message", corpo))

    def encerrar(self, sessao_id: str) -> None:
        self._requisitar("DELETE", f"/sessions/{sessao_id}")


def criar_cliente(config) -> WatsonClient | None:
    chave = (config.get("WATSON_API_KEY") or "").strip()
    url = (config.get("WATSON_URL") or "").strip()
    assistente = (config.get("WATSON_ASSISTANT_ID") or "").strip()
    if not (chave and url and assistente):
        return None
    return WatsonClient(
        chave,
        url,
        assistente,
        config["WATSON_VERSION"],
        float(config["WATSON_TIMEOUT"]),
        environment_id=(config.get("WATSON_ENVIRONMENT_ID") or "").strip() or None,
        iam_url=(config.get("WATSON_IAM_URL") or IAM_PADRAO).strip(),
    )
