from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class DadosPaciente(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    idade_media: float = Field(ge=0, le=120)
    carga_sistema: float = Field(ge=0, le=100)
    tempo_espera: float = Field(ge=0, le=1440)
    fc_media: float = Field(ge=20, le=250)
    spo2_media: float = Field(ge=0, le=100)
    pa_sistolica: float = Field(ge=40, le=300)
    temperatura: float = Field(ge=-20, le=60)
    densidade_eventos: float = Field(ge=0, le=100)
    eventos_24h: float = Field(ge=0, le=1000)
    disponibilidade_recursos: float = Field(
        ge=0,
        le=100,
        validation_alias=AliasChoices("disponibilidade_recursos", "disponibilidade recursos"),
    )


class LeituraSensor(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)

    paciente_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    fc_media: float = Field(ge=20, le=250)
    temperatura: float = Field(ge=-20, le=60)
    spo2_media: float | None = Field(default=None, ge=0, le=100)
    pa_sistolica: float | None = Field(default=None, ge=40, le=300)
    dispositivo: str | None = Field(default=None, max_length=60)


class ParametrosOperacionais(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    carga_sistema: float | None = Field(default=None, ge=0, le=100)
    tempo_espera: float | None = Field(default=None, ge=0, le=1440)
    disponibilidade_recursos: float | None = Field(default=None, ge=0, le=100)
    densidade_eventos: float | None = Field(default=None, ge=0, le=100)
