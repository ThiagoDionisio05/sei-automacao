"""Ponto de entrada da automação de criação de processos/documentos no SEI.

Uso:
    python main.py                     # dry-run (padrão): só 1 processo, sem salvar
    python main.py --run               # execução real, todos os processos pendentes (só o processo, sem documentos)
    python main.py --run --linha 3     # execução real, apenas a linha 3 da planilha
    python main.py --run --com-documentos  # também inclui os documentos após criar o processo
"""

import argparse

from playwright.sync_api import sync_playwright

from src import config
from src.browser import abrir_sessao
from src.planilha import (
    carregar_processos,
    carregar_status,
    ja_processado,
    marcar_processado,
    marcar_processo_criado,
)
from src.processo import atribuir_processo, iniciar_processo, relacionar_processo, sair_do_processo
from src.documento import incluir_documentos_padrao
from src.painel import atualizar_painel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run",
        action="store_true",
        help="Executa de verdade (salva no SEI). Sem essa flag, roda em dry-run.",
    )
    parser.add_argument(
        "--linha",
        type=int,
        default=None,
        help="Processa apenas uma linha específica da planilha (índice, começando em 0).",
    )
    parser.add_argument(
        "--com-documentos",
        action="store_true",
        help="Também inclui os documentos após criar o processo. Sem essa flag, só cria o processo (etapa atual em validação).",
    )
    args = parser.parse_args()
    dry_run = not args.run

    processos = carregar_processos()
    status = carregar_status()

    if args.linha is not None:
        processos = [p for p in processos if p.linha == args.linha]

    if dry_run:
        processos = processos[:1]
        print("=== MODO DRY-RUN: apenas 1 processo, nada será salvo ===\n")

    pendentes = [p for p in processos if not ja_processado(status, p.linha)]
    if not pendentes:
        print("Nada a processar (tudo já concluído ou nenhuma linha selecionada).")
        return

    sucesso = []
    pulados = []
    falhas = []

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)

        for processo in pendentes:
            print(f"\n--- Processando linha {processo.linha} ---")

            existente = status.get(str(processo.linha), {})
            numero_existente = existente.get("numero_processo_sei")
            if numero_existente and numero_existente != "SALVO-NUMERO-DESCONHECIDO":
                print(
                    f"Linha {processo.linha} já tem processo criado ({numero_existente}) de uma "
                    "tentativa anterior que não terminou. Pulando a criação pra não duplicar o "
                    f"processo — complete manualmente com: python testar_documento.py {numero_existente}"
                )
                pulados.append((processo.linha, numero_existente))
                continue

            try:
                numero = iniciar_processo(page, processo, dry_run)

                if not dry_run:
                    marcar_processo_criado(status, processo.linha, numero)
                    atualizar_painel()
                    atribuir_processo(page, numero)
                    relacionar_processo(page, numero)

                if args.com_documentos:
                    incluir_documentos_padrao(page, numero, dry_run, verificar_existentes=False)
                    if not dry_run:
                        sair_do_processo(page, numero)
                else:
                    print("(Documentos não incluídos nesta etapa — use --com-documentos quando estiver pronto.)")

                if not dry_run:
                    marcar_processado(status, processo.linha, numero)
                    atualizar_painel()

                sucesso.append((processo.linha, numero))

            except Exception as exc:
                print(f"ERRO na linha {processo.linha}: {exc}")
                print("Pulando pra próxima linha — esse processo fica pra você conferir/completar depois.")
                falhas.append((processo.linha, str(exc)))
                continue

        print("\nConcluído.")
        print(f"  Sucesso: {len(sucesso)} | Pulados (já existiam): {len(pulados)} | Falhas: {len(falhas)}")
        if falhas:
            print("\nLinhas com erro (confira manualmente no SEI):")
            for linha, erro in falhas:
                print(f"  - linha {linha}: {erro}")
        if pulados:
            print("\nLinhas puladas (processo já criado antes, complete com testar_documento.py):")
            for linha, numero in pulados:
                print(f"  - linha {linha}: {numero}")
        if not dry_run:
            print("\nLembre-se: os documentos NÃO foram assinados. Assine manualmente no SEI.")

        # Não fecha o navegador — é o Chrome que você abriu manualmente,
        # continua sob seu controle depois que a automação termina.


if __name__ == "__main__":
    main()



