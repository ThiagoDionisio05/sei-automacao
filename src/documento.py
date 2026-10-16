"""Inclusão de documentos dentro de um processo já criado no SEI."""

from datetime import date

from playwright.sync_api import Page

from . import config, sei_page


def incluir_documento(
    page: Page,
    numero_processo: str,
    tipo_documento: str,
    conteudo: str,
    dry_run: bool,
    nome_arvore: str = None,
    arquivo_anexo=None,
) -> None:
    """Registra um Documento Externo dentro do processo atualmente aberto.

    Assume que o processo `numero_processo` já está aberto na tela
    (chamado logo após `iniciar_processo`, ou logo após o documento anterior
    ter sido salvo, para incluir mais de um documento no mesmo processo).

    `nome_arvore` e `arquivo_anexo` permitem reutilizar esta função para
    documentos diferentes (ex.: Nota Técnica, Despacho) — quando omitidos,
    usam os padrões da Nota Técnica em config.py.
    """
    if nome_arvore is None:
        nome_arvore = config.NOME_ARVORE_PADRAO
    if arquivo_anexo is None:
        arquivo_anexo = config.ARQUIVO_ANEXO_PADRAO

    numero_seguro = numero_processo.replace("/", "-")

    sei_page.marcar_tempo(f"{numero_seguro}: início do documento")

    page.wait_for_timeout(500)
    sei_page.clicar_por_texto_ou_icone(page, "Incluir Documento")
    sei_page.esperar_carregar(page)
    sei_page.screenshot(page, f"doc_{numero_seguro}_tela_apos_clique")
    sei_page.marcar_tempo(f"{numero_seguro}: clicou Incluir Documento")

    frame = sei_page.frame_conteudo(page)
    sei_page.buscar_e_selecionar(frame, config.TIPO_DOCUMENTO_PADRAO)
    sei_page.esperar_carregar(page)
    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_escolher_tipo")
    sei_page.marcar_tempo(f"{numero_seguro}: escolheu tipo Externo")

    frame = sei_page.frame_conteudo(page)

    ok_tipo = sei_page.selecionar_select_por_rotulo(
        frame, "Tipo do Documento", config.TIPO_DOCUMENTO_EXTERNO_PADRAO
    )

    data_hoje = date.today().strftime("%d/%m/%Y")
    sei_page.digitar_por_rotulo_ou_seletor(
        frame, "Data do Documento", config.SELECTORS.get("campo_data_documento", ""), data_hoje
    )

    sei_page.digitar_por_rotulo_ou_seletor(
        frame, "Nome na Árvore", config.SELECTORS["campo_nome_arvore"], nome_arvore
    )

    marcou_formato = sei_page.marcar_radio(frame, "Nato-digital")
    marcou_nivel = sei_page.marcar_radio(frame, "Público")

    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_campos_externo")
    sei_page.marcar_tempo(f"{numero_seguro}: preencheu campos (tipo/data/árvore/formato/nível)")

    if not ok_tipo:
        sei_page.screenshot(page, f"doc_{numero_seguro}_erro_tipo_documento")
        raise RuntimeError(
            f"Não consegui selecionar o Tipo do Documento (contendo "
            f"'{config.TIPO_DOCUMENTO_EXTERNO_PADRAO}') no processo {numero_processo}. "
            f"Confira o screenshot doc_{numero_seguro}_erro_tipo_documento.png e verifique "
            "manualmente no SEI antes de tentar de novo."
        )

    if not marcou_formato or not marcou_nivel:
        faltando = []
        if not marcou_formato:
            faltando.append("Formato 'Nato-digital'")
        if not marcou_nivel:
            faltando.append("Nível de Acesso 'Público'")
        sei_page.screenshot(page, f"doc_{numero_seguro}_erro_formato_nivel")
        raise RuntimeError(
            f"Não consegui marcar: {', '.join(faltando)} (processo {numero_processo}). "
            f"Confira o screenshot doc_{numero_seguro}_erro_formato_nivel.png e verifique "
            "manualmente no SEI antes de tentar de novo."
        )

    anexou = sei_page.anexar_arquivo(frame, arquivo_anexo, timeout_ms=8000)

    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_anexar_arquivo")
    sei_page.marcar_tempo(f"{numero_seguro}: anexou arquivo")

    if not anexou:
        sei_page.screenshot(page, f"doc_{numero_seguro}_erro_nao_anexou")
        raise RuntimeError(
            f"Campos preenchidos, mas não consegui confirmar o anexo do arquivo "
            f"({arquivo_anexo}) no processo {numero_processo}. Confira o screenshot "
            f"doc_{numero_seguro}_erro_nao_anexou.png e verifique manualmente no SEI "
            "antes de tentar de novo."
        )

    sei_page.clicar_botao(frame, "Salvar")
    sei_page.esperar_carregar(page)
    page.wait_for_timeout(400)

    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_salvar")
    sei_page.marcar_tempo(f"{numero_seguro}: salvou")

    # Recarrega antes de verificar: a árvore (pane da esquerda) às vezes não
    # atualiza sozinha logo após o Salvar, o que dava falso negativo aqui
    # (documento salvo de verdade, mas ainda não refletido na árvore).
    page.reload()
    sei_page.esperar_carregar(page)
    sei_page.marcar_tempo(f"{numero_seguro}: recarregou pra verificar")

    if not sei_page.documento_existe_na_arvore(page, nome_arvore):
        sei_page.screenshot(page, f"doc_{numero_seguro}_erro_nao_apareceu_na_arvore")
        raise RuntimeError(
            f"Cliquei em Salvar, mas '{nome_arvore}' não apareceu na árvore do processo "
            f"{numero_processo} depois — o documento provavelmente NÃO foi anexado de "
            f"verdade. Confira o screenshot doc_{numero_seguro}_erro_nao_apareceu_na_arvore.png "
            "e verifique manualmente no SEI antes de tentar de novo."
        )

    print(
        f"Documento externo salvo no processo {numero_processo}. Confira o screenshot "
        "para conferir o resultado."
    )


DOCUMENTOS_PADRAO = [
    ("Nota Técnica", config.NOME_ARVORE_PADRAO, config.ARQUIVO_ANEXO_PADRAO),
    ("Despacho", config.NOME_ARVORE_DESPACHO, config.ARQUIVO_ANEXO_DESPACHO),
    ("Despacho de Unificação de Planilhas", config.NOME_ARVORE_UNIFICACAO, config.ARQUIVO_ANEXO_UNIFICACAO),
    ("Despacho de Aprovação do Plano de Trabalho de Processos", config.NOME_ARVORE_APROVACAO, config.ARQUIVO_ANEXO_APROVACAO),
]


def incluir_documentos_padrao(
    page: Page, numero_processo: str, dry_run: bool, verificar_existentes: bool = True
) -> None:
    """Garante que o processo aberto tenha os 4 documentos padrão (Nota
    Técnica, Despacho, Despacho de Unificação de Planilhas e Despacho de
    Aprovação do Plano de Trabalho de Processos), na ordem acima.

    `verificar_existentes=True` (padrão) checa cada um na árvore antes de
    criar e pula os que já existirem — necessário ao reprocessar um
    processo que pode já ter alguns documentos (veja testar_documento.py).
    `verificar_existentes=False` cria os 4 direto, sem checar — use quando
    o processo é recém-criado (main.py), onde a checagem é só espera
    desnecessária (o processo nunca tem documento nenhum ainda).
    """
    for rotulo, nome_arvore, arquivo_anexo in DOCUMENTOS_PADRAO:
        if verificar_existentes and sei_page.documento_existe_na_arvore(page, nome_arvore):
            print(f"{rotulo} já existe no processo {numero_processo} — pulando.")
            continue

        incluir_documento(
            page,
            numero_processo,
            "",
            "",
            dry_run,
            nome_arvore=nome_arvore,
            arquivo_anexo=arquivo_anexo,
        )
