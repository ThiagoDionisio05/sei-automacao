"""Gera dados_processos.js a partir de status/processados.json, pro painel
HTML (painel_processos.html) mostrar os processos automaticamente.
"""

import json

from . import config

PAINEL_DADOS_FILE = config.BASE_DIR / "dados_processos.js"


def atualizar_painel() -> None:
    """Regrava dados_processos.js com os números de processo atuais.

    Inclui todo processo com número real gerado no SEI, mesmo que o resto
    do fluxo (atribuir/relacionar/documentos) não tenha terminado — status
    "processo_criado" ou "concluido", ambos aparecem. Só entram processos
    criados em `config.PAINEL_DATA_CORTE` ou depois (histórico anterior
    fica de fora, sem ser apagado do status.json). Chamado logo após o
    processo ser criado E de novo ao final de cada linha, pra manter o
    painel sempre sincronizado sem precisar de nenhum passo manual.
    """
    if not config.STATUS_FILE.exists():
        processos = []
    else:
        status = json.loads(config.STATUS_FILE.read_text(encoding="utf-8"))
        processos = [
            {"numero": info["numero_processo_sei"], "status": info.get("status", "")}
            for _, info in sorted(status.items(), key=lambda item: int(item[0]))
            if info.get("numero_processo_sei")
            and info.get("numero_processo_sei") != "SALVO-NUMERO-DESCONHECIDO"
            and info.get("criado_em", "") >= config.PAINEL_DATA_CORTE
        ]

    conteudo = (
        "// Gerado automaticamente por src/painel.py — não edite à mão.\n"
        "window.PROCESSOS_ORIGINAIS = " + json.dumps(processos, ensure_ascii=False, indent=2) + ";\n"
    )
    PAINEL_DADOS_FILE.write_text(conteudo, encoding="utf-8")
