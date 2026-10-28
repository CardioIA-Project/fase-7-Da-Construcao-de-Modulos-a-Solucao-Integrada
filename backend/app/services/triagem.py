from __future__ import annotations

import re
import threading
import time
import unicodedata
import uuid
from dataclasses import dataclass, field

MAX_TENTATIVAS = 3
MAX_SESSOES = 2000
TTL_SESSAO_S = 3600

SINTOMAS = [
    {
        "rotulo": "Dor no peito",
        "emergencia": True,
        "sinonimos": ["dor no peito", "aperto no peito", "pressao no peito", "peito apertado", "dor toracica"],
        "padroes": [
            [r"\b(peito|torax|toracic\w*)\b", r"\b(apert\w*|dor\w*|doendo|pressao|queimand\w*|esmagand\w*)\b"],
        ],
    },
    {
        "rotulo": "Falta de ar",
        "emergencia": True,
        "sinonimos": ["falta de ar", "dificuldade de respirar", "dificuldade para respirar"],
        "padroes": [
            [r"\bsem ar\b"],
            [r"\b(respirar|respiracao|folego)\b", r"\b(dific\w*|nao consigo|custo|ofegante|curt\w*|falta)\b"],
        ],
    },
    {
        "rotulo": "Palpitação",
        "emergencia": False,
        "sinonimos": ["palpitacao", "palpitacoes", "coracao acelerado", "coracao disparado"],
        "padroes": [],
    },
    {
        "rotulo": "Tontura",
        "emergencia": False,
        "sinonimos": ["tontura", "tonturas", "vertigem"],
        "padroes": [],
    },
    {
        "rotulo": "Cansaço",
        "emergencia": False,
        "sinonimos": ["cansaco", "cansado", "cansada", "fadiga"],
        "padroes": [],
    },
    {
        "rotulo": "Inchaço nas pernas",
        "emergencia": False,
        "sinonimos": ["inchaco nas pernas", "pernas inchadas", "inchaco"],
        "padroes": [],
    },
    {
        "rotulo": "Dor no braço",
        "emergencia": True,
        "sinonimos": ["dor no braco", "formigamento no braco", "braco dormente"],
        "padroes": [
            [r"\bbraco\b", r"\b(dor\w*|doendo|formig\w*|dorm\w*|pesad\w*)\b"],
        ],
    },
    {
        "rotulo": "Suor frio",
        "emergencia": True,
        "sinonimos": ["suor frio", "suando frio", "suei frio"],
        "padroes": [
            [r"\b(suor|suando|suei|suar)\b", r"\bfrio\b"],
        ],
    },
]

SINTOMAS_POR_PRIORIDADE = sorted(SINTOMAS, key=lambda s: not s["emergencia"])

SEVERIDADES = ["Leve", "Moderada", "Intensa"]
DURACOES = ["Minutos", "Horas", "Dias", "Semanas"]

FATORES = [
    ("hipertensao", "hipertensão"),
    ("hipertenso", "hipertensão"),
    ("pressao alta", "hipertensão"),
    ("diabetes", "diabetes"),
    ("diabetico", "diabetes"),
    ("colesterol", "colesterol alto"),
    ("tabag", "tabagismo"),
    ("fumo", "tabagismo"),
    ("fumante", "tabagismo"),
    ("obesidade", "obesidade"),
    ("obeso", "obesidade"),
    ("sedentar", "sedentarismo"),
    ("historico familiar", "histórico familiar de problema cardíaco"),
    ("familiar", "histórico familiar de problema cardíaco"),
]

NEGATIVAS = {"nenhum", "nenhuma", "nao", "nao tenho", "nada", "n"}

BOAS_VINDAS = "Bem-vindo, como posso ajudá-lo?"
PERGUNTA_SINTOMA = (
    "Entendi. Esse assistente faz uma triagem inicial e não substitui uma avaliação médica. "
    "Qual sintoma você está sentindo?"
)
PERGUNTA_SEVERIDADE = "Entendido. Numa escala de leve, moderada ou intensa, como você classificaria esse sintoma?"
PERGUNTA_DURACAO = "Há quanto tempo você sente esse sintoma?"
PERGUNTA_FATORES = (
    "Você tem algum desses fatores de risco: hipertensão, diabetes, colesterol alto, tabagismo, "
    "obesidade, sedentarismo ou histórico familiar de problema cardíaco? "
    "Pode citar mais de um, ou responder 'nenhum'."
)
NAO_ENTENDI = "Eu não entendi. Selecione uma opção válida:"
FALLBACK = (
    "Não consegui entender suas respostas. Se estiver sentindo algo preocupante, procure um "
    "atendimento médico. Envie uma nova mensagem para reiniciar a triagem."
)
EMERGENCIA = (
    "Pelos sintomas relatados, isso pode ser uma emergência cardíaca. Ligue agora para o SAMU (192) "
    "ou procure o pronto-socorro mais próximo. Não aguarde — cada minuto importa. Esse assistente "
    "não pode fazer diagnóstico, e a orientação mais segura agora é buscar atendimento médico imediato."
)


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    limpo = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return " ".join(limpo.split())


def _escolher(texto: str, opcoes: list[str]) -> str | None:
    alvo = normalizar(texto)
    if alvo.isdigit() and 1 <= int(alvo) <= len(opcoes):
        return opcoes[int(alvo) - 1]
    for opcao in opcoes:
        if normalizar(opcao) == alvo:
            return opcao
    return None


def _casa(sintoma: dict, alvo: str) -> bool:
    if any(re.search(r"\b" + re.escape(sin) + r"\b", alvo) for sin in sintoma["sinonimos"]):
        return True
    for padrao in sintoma["padroes"]:
        if all(re.search(parte, alvo) for parte in padrao):
            return True
    return False


def _detectar_sintoma(texto: str) -> dict | None:
    alvo = normalizar(texto)
    rotulos = [s["rotulo"] for s in SINTOMAS]
    escolhido = _escolher(texto, rotulos)
    if escolhido:
        return next(s for s in SINTOMAS if s["rotulo"] == escolhido)
    for sintoma in SINTOMAS_POR_PRIORIDADE:
        if _casa(sintoma, alvo):
            return sintoma
    return None


def _detectar_opcao(texto: str, opcoes: list[str]) -> str | None:
    escolhido = _escolher(texto, opcoes)
    if escolhido:
        return escolhido
    alvo = normalizar(texto)
    for opcao in opcoes:
        if normalizar(opcao) in alvo.split():
            return opcao
    return None


def _detectar_fatores(texto: str) -> list[str]:
    alvo = normalizar(texto)
    if alvo in NEGATIVAS:
        return []
    encontrados: list[str] = []
    for chave, rotulo in FATORES:
        if chave in alvo and rotulo not in encontrados:
            encontrados.append(rotulo)
    return encontrados


@dataclass
class Sessao:
    id: str
    etapa: str = "inicio"
    sintoma: str | None = None
    severidade: str | None = None
    duracao: str | None = None
    fatores: list[str] = field(default_factory=list)
    tentativas: int = 0
    ultimo_uso: float = field(default_factory=time.monotonic)


def _resposta(mensagens: list[str], opcoes: list[str] | None = None, emergencia: bool = False,
              finalizado: bool = False) -> dict:
    return {
        "replies": mensagens,
        "options": opcoes or [],
        "emergencia": emergencia,
        "finalizado": finalizado,
    }


def _resumo(sessao: Sessao) -> str:
    partes = [
        f"Resumindo o que você me contou: você relatou o sintoma {sessao.sintoma}, "
        f"classificado como {sessao.severidade}, há {sessao.duracao}."
    ]
    if sessao.fatores:
        partes.append("Fatores de risco informados: " + ", ".join(sessao.fatores) + ".")
    else:
        partes.append("Você não informou fatores de risco.")
    partes.append(
        "Isso não é um diagnóstico — recomendo fortemente que você procure um cardiologista "
        "para uma avaliação completa. Se os sintomas piorarem, procure atendimento de emergência."
    )
    if sessao.severidade == "Intensa":
        partes.append("Como a intensidade é alta, não adie a avaliação médica.")
    return " ".join(partes)


class TriagemService:
    def __init__(self) -> None:
        self._sessoes: dict[str, Sessao] = {}
        self._trava = threading.Lock()

    def _limpar(self) -> None:
        limite = time.monotonic() - TTL_SESSAO_S
        for chave in [k for k, s in self._sessoes.items() if s.ultimo_uso < limite]:
            del self._sessoes[chave]
        excesso = len(self._sessoes) - MAX_SESSOES + 1
        if excesso > 0:
            antigas = sorted(self._sessoes.values(), key=lambda s: s.ultimo_uso)[:excesso]
            for sessao in antigas:
                del self._sessoes[sessao.id]

    def criar_sessao(self) -> str:
        sessao = Sessao(id=uuid.uuid4().hex)
        with self._trava:
            self._limpar()
            self._sessoes[sessao.id] = sessao
        return sessao.id

    def encerrar_sessao(self, sessao_id: str) -> bool:
        with self._trava:
            return self._sessoes.pop(sessao_id, None) is not None

    def existe(self, sessao_id: str) -> bool:
        with self._trava:
            return sessao_id in self._sessoes

    def responder(self, sessao_id: str, texto: str) -> dict | None:
        with self._trava:
            sessao = self._sessoes.get(sessao_id)
            if sessao is None:
                return None
            if time.monotonic() - sessao.ultimo_uso > TTL_SESSAO_S:
                del self._sessoes[sessao_id]
                return None
            sessao.ultimo_uso = time.monotonic()
            return self._avancar(sessao, texto)

    def _reiniciar(self, sessao: Sessao) -> None:
        sessao.etapa = "inicio"
        sessao.sintoma = sessao.severidade = sessao.duracao = None
        sessao.fatores = []
        sessao.tentativas = 0

    def _pedir_sintoma(self, sessao: Sessao, prefixo: list[str] | None = None) -> dict:
        sessao.etapa = "sintoma"
        sessao.tentativas = 0
        return _resposta((prefixo or []) + [PERGUNTA_SINTOMA], [s["rotulo"] for s in SINTOMAS])

    def _processar_sintoma(self, sessao: Sessao, sintoma: dict) -> dict:
        sessao.sintoma = sintoma["rotulo"]
        sessao.tentativas = 0
        if sintoma["emergencia"]:
            sessao.etapa = "fim"
            return _resposta([EMERGENCIA], emergencia=True, finalizado=True)
        sessao.etapa = "severidade"
        return _resposta([PERGUNTA_SEVERIDADE], SEVERIDADES)

    def _falha(self, sessao: Sessao, opcoes: list[str]) -> dict:
        sessao.tentativas += 1
        if sessao.tentativas >= MAX_TENTATIVAS:
            sessao.etapa = "fim"
            return _resposta([FALLBACK], finalizado=True)
        return _resposta([NAO_ENTENDI], opcoes)

    def _avancar(self, sessao: Sessao, texto: str) -> dict:
        texto = (texto or "").strip()

        if sessao.etapa == "fim":
            self._reiniciar(sessao)

        if sessao.etapa == "inicio":
            sintoma = _detectar_sintoma(texto)
            if sintoma:
                return self._processar_sintoma(sessao, sintoma)
            return self._pedir_sintoma(sessao, [BOAS_VINDAS])

        if sessao.etapa == "sintoma":
            sintoma = _detectar_sintoma(texto)
            if sintoma:
                return self._processar_sintoma(sessao, sintoma)
            return self._falha(sessao, [s["rotulo"] for s in SINTOMAS])

        if sessao.etapa == "severidade":
            escolha = _detectar_opcao(texto, SEVERIDADES)
            if escolha:
                sessao.severidade = escolha
                sessao.tentativas = 0
                sessao.etapa = "duracao"
                return _resposta([PERGUNTA_DURACAO], DURACOES)
            return self._falha(sessao, SEVERIDADES)

        if sessao.etapa == "duracao":
            escolha = _detectar_opcao(texto, DURACOES)
            if escolha:
                sessao.duracao = escolha.lower()
                sessao.tentativas = 0
                sessao.etapa = "fatores"
                return _resposta([PERGUNTA_FATORES])
            return self._falha(sessao, DURACOES)

        if sessao.etapa == "fatores":
            sessao.fatores = _detectar_fatores(texto)
            sessao.etapa = "fim"
            return _resposta([_resumo(sessao)], finalizado=True)

        self._reiniciar(sessao)
        return self._pedir_sintoma(sessao, [BOAS_VINDAS])
