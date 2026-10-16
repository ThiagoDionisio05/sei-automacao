"""Gera data/processos.xlsx de exemplo com as colunas esperadas."""

import pandas as pd

from . import config

if __name__ == "__main__":
    colunas = {
        "tipo_processo": ["Benefício: Concessão", "Benefício: Revisão"],
        "especificacao": ["Especificação de exemplo 1", "Especificação de exemplo 2"],
    }

    df = pd.DataFrame(colunas)
    config.DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(config.DATA_FILE, index=False)
    print(f"Planilha de exemplo criada em: {config.DATA_FILE}")
