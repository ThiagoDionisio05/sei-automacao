"""Testa só o passo de "Incluir Documento" num processo que JÁ está aberto
na tela do SEI (não cria processo novo).

Uso:
    python testar_documento.py 00000.000000/0000-00             # os 4 documentos padrão (pula os que já existirem)
    python testar_documento.py 00000.000000/0000-00 nota         # só a Nota Técnica
    python testar_documento.py 00000.000000/0000-00 despacho     # só o Despacho
    python testar_documento.py 00000.000000/0000-00 unificacao   # só o Despacho de Unificação de Planilhas
    python testar_documento.py 00000.000000/0000-00 aprovacao    # só o Despacho de Aprovação do Plano de Trabalho de Processos
"""

import sys

from playwright.sync_api import sync_playwright

from src import config
from src.browser import abrir_sessao
from src.documento import incluir_documento, incluir_documentos_padrao

MODOS = {
    "nota": (config.NOME_ARVORE_PADRAO, config.ARQUIVO_ANEXO_PADRAO),
    "despacho": (config.NOME_ARVORE_DESPACHO, config.ARQUIVO_ANEXO_DESPACHO),
    "unificacao": (config.NOME_ARVORE_UNIFICACAO, config.ARQUIVO_ANEXO_UNIFICACAO),
    "aprovacao": (config.NOME_ARVORE_APROVACAO, config.ARQUIVO_ANEXO_APROVACAO),
}


def main():
    numero_processo = sys.argv[1] if len(sys.argv) > 1 else "processo-aberto-na-tela"
    modo = sys.argv[2].lower() if len(sys.argv) > 2 else "todos"

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)

        print(f"\nCertifique-se que o processo {numero_processo} já está aberto na tela.")
        print("Pressione ENTER para continuar.")
        input()

        if modo in MODOS:
            nome_arvore, arquivo_anexo = MODOS[modo]
            incluir_documento(
                page,
                numero_processo,
                "",
                "",
                dry_run=False,
                nome_arvore=nome_arvore,
                arquivo_anexo=arquivo_anexo,
            )
        else:
            incluir_documentos_padrao(page, numero_processo, dry_run=False)


if __name__ == "__main__":
    main()
