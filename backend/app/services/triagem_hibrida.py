from __future__ import annotations

import logging
import threading
import time

from .triagem import TriagemService

logger = logging.getLogger(__name__)

FALHAS_PARA_ABRIR = 3
PAUSA_CIRCUITO_S = 60

MARCA_RESUMO = "Resumindo o que você me contou"
MARCA_EMERGENCIA = "SAMU (192)"
MARCA_NAO_ENTENDI = "não entendi"


class TriagemHibrida:
    def __init__(self, local: TriagemService, watson=None) -> None:
        self._local = local
        self._watson = watson
        self._sessoes_watson: dict[str, str] = {}
        self._falhas = 0
        self._bloqueado_ate = 0.0
        self._trava = threading.Lock()

    @property
    def watson_configurado(self) -> bool:
        return self._watson is not None

    @property
    def watson_ativo(self) -> bool:
        return self._watson is not None and time.monotonic() >= self._bloqueado_ate

    def _registrar_falha(self, erro: Exception) -> None:
        with self._trava:
            self._falhas += 1
            if self._falhas >= FALHAS_PARA_ABRIR:
                self._bloqueado_ate = time.monotonic() + PAUSA_CIRCUITO_S
                self._falhas = 0
                logger.warning("Watson indisponível, usando triagem local por %ss: %s", PAUSA_CIRCUITO_S, erro)
            else:
                logger.warning("Falha ao chamar o Watson: %s", erro)

    def _registrar_sucesso(self) -> None:
        with self._trava:
            self._falhas = 0

    def _limpar_mapa(self) -> None:
        for chave in [k for k in list(self._sessoes_watson) if not self._local.existe(k)]:
            self._sessoes_watson.pop(chave, None)

    def criar_sessao(self) -> str:
        sessao_id = self._local.criar_sessao()
        with self._trava:
            self._limpar_mapa()
        if self.watson_ativo:
            try:
                sessao_watson = self._watson.criar_sessao()
            except Exception as erro:
                self._registrar_falha(erro)
            else:
                self._registrar_sucesso()
                with self._trava:
                    self._sessoes_watson[sessao_id] = sessao_watson
        return sessao_id

    def existe(self, sessao_id: str) -> bool:
        return self._local.existe(sessao_id)

    def responder(self, sessao_id: str, texto: str) -> dict | None:
        local = self._local.responder(sessao_id, texto)
        if local is None:
            self._sessoes_watson.pop(sessao_id, None)
            return None
        resposta_local = {**local, "origem": "local"}
        if local["emergencia"]:
            return resposta_local
        sessao_watson = self._sessoes_watson.get(sessao_id)
        if sessao_watson is None or not self.watson_ativo or not texto.strip():
            return resposta_local
        try:
            watson = self._watson.enviar(sessao_watson, texto)
        except Exception as erro:
            self._registrar_falha(erro)
            return resposta_local
        if not watson["replies"] and not watson["options"]:
            return resposta_local
        self._registrar_sucesso()
        junto = " ".join(watson["replies"])
        if MARCA_NAO_ENTENDI in junto.lower() and local["options"]:
            return resposta_local
        emergencia = MARCA_EMERGENCIA in junto
        finalizado = emergencia or MARCA_RESUMO in junto or local["finalizado"]
        return {
            "replies": watson["replies"],
            "options": watson["options"],
            "emergencia": emergencia,
            "finalizado": finalizado,
            "origem": "watson",
        }

    def encerrar_sessao(self, sessao_id: str) -> bool:
        sessao_watson = self._sessoes_watson.pop(sessao_id, None)
        if sessao_watson is not None and self._watson is not None:
            try:
                self._watson.encerrar(sessao_watson)
            except Exception as erro:
                logger.warning("Falha ao encerrar sessão no Watson: %s", erro)
        return self._local.encerrar_sessao(sessao_id)
