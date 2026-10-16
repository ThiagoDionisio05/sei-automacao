"""Leitura da planilha de entrada e controle de status (idempotência)."""

import json
from dataclasses import dataclass
from datetime import date

import pandas as pd

from . import config


@dataclass
class Processo:
    linha: int
    tipo_processo: str
    especificacao: str


def carregar_processos() -> list[Processo]:
    df = pd.read_excel(config.DATA_FILE)

    obrigatorias = {"tipo_processo", "especificacao"}
    faltando = obrigatorias - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas obrigatórias ausentes na planilha: {faltando}")

    processos = []
    for idx, row in df.iterrows():
        processos.append(
            Processo(
                linha=idx,
                tipo_processo=str(row["tipo_processo"]),
                especificacao=str(row["especificacao"]),
            )
        )
    return processos


def carregar_status() -> dict:
    if not config.STATUS_FILE.exists():
        return {}
    return json.loads(config.STATUS_FILE.read_text(encoding="utf-8"))


def salvar_status(status: dict) -> None:
    config.STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.STATUS_FILE.write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def marcar_processo_criado(status: dict, linha: int, numero_processo_sei: str) -> None:
    """Registra que o processo já foi criado no SEI (número real gerado),
    mesmo que o resto do fluxo (atribuir/relacionar/documentos) ainda não
    tenha terminado. Chamado logo após `iniciar_processo`, pra o processo
    aparecer no painel mesmo se algo falhar depois.
    """
    status[str(linha)] = {
        "numero_processo_sei": numero_processo_sei,
        "status": "processo_criado",
        "criado_em": date.today().isoformat(),
    }
    salvar_status(status)


def marcar_processado(status: dict, linha: int, numero_processo_sei: str) -> None:
    # Preserva a data de criação original (gravada por marcar_processo_criado)
    # se já existir, em vez de sobrescrever com a data de hoje.
    criado_em = status.get(str(linha), {}).get("criado_em") or date.today().isoformat()
    status[str(linha)] = {
        "numero_processo_sei": numero_processo_sei,
        "status": "concluido",
        "criado_em": criado_em,
    }
    salvar_status(status)


def ja_processado(status: dict, linha: int) -> bool:
    return str(linha) in status and status[str(linha)].get("status") == "concluido"
