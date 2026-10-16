"""Criação de processo no SEI."""

from playwright.sync_api import Page

from . import config, sei_page
from .planilha import Processo


def iniciar_processo(page: Page, processo: Processo, dry_run: bool) -> str:
    """Cria um novo processo no SEI e retorna o número gerado.

    Se dry_run=True, preenche o formulário mas NÃO clica em salvar —
    tira um screenshot para você validar visualmente e conferir os seletores.
    """
    sel = config.SELECTORS

    sei_page.marcar_tempo(f"linha{processo.linha}: início")

    sei_page.clicar_por_texto_ou_icone(page, "Iniciar Processo")
    sei_page.esperar_carregar(page)
    sei_page.screenshot(page, f"processo_linha{processo.linha}_tela_apos_clique")
    sei_page.marcar_tempo(f"linha{processo.linha}: clicou Iniciar Processo")

    frame = sei_page.frame_conteudo(page)
    sei_page.buscar_e_selecionar(frame, config.TIPO_PROCESSO_PADRAO)

    sei_page.esperar_carregar(page)
    sei_page.screenshot(page, f"processo_linha{processo.linha}_apos_escolher_tipo")
    sei_page.marcar_tempo(f"linha{processo.linha}: escolheu tipo de processo")

    frame = sei_page.frame_conteudo(page)
    frame.fill(sel["campo_especificacao"], processo.especificacao)

    sei_page.selecionar_nivel_acesso(frame, config.NIVEL_ACESSO_PADRAO)

    if config.NIVEL_ACESSO_PADRAO in ("restrito", "sigiloso"):
        sei_page.selecionar_hipotese_legal(frame, config.HIPOTESE_LEGAL_PADRAO)

    sei_page.screenshot(page, f"processo_linha{processo.linha}_antes_salvar")
    sei_page.marcar_tempo(f"linha{processo.linha}: preencheu campos do processo")

    if dry_run:
        print(
            f"[DRY-RUN] Processo (linha {processo.linha}) preenchido, "
            "NÃO salvo. Confira o screenshot e valide os seletores."
        )
        return "DRY-RUN"

    sei_page.clicar_botao(frame, "Salvar")
    sei_page.esperar_carregar(page)
    page.wait_for_timeout(400)

    frame = sei_page.frame_conteudo(page)

    ainda_no_formulario = False
    try:
        ainda_no_formulario = frame.locator(sel["campo_especificacao"]).first.is_visible()
    except Exception:
        ainda_no_formulario = False

    if ainda_no_formulario:
        erro = sei_page.procurar_mensagem_erro(frame)
        sei_page.screenshot(page, f"processo_linha{processo.linha}_erro_ao_salvar")
        raise RuntimeError(
            f"O Salvar não completou para a linha {processo.linha} — ainda estou na tela do "
            "formulário (não navegou para o processo criado). "
            + (f"Mensagem de erro encontrada: {erro!r}" if erro else "Nenhuma mensagem de erro visível; confira o screenshot processo_linha" + str(processo.linha) + "_erro_ao_salvar.png.")
        )

    erro_pagina = sei_page.detectar_pagina_erro(page)
    if erro_pagina:
        sei_page.screenshot(page, f"processo_linha{processo.linha}_erro_ao_salvar")
        raise RuntimeError(
            f"O SEI retornou uma página de erro ao salvar a linha {processo.linha}: {erro_pagina!r}. "
            f"Confira o screenshot processo_linha{processo.linha}_erro_ao_salvar.png."
        )

    caiu_no_controle_processos = sei_page.esta_em_controle_processos(page)

    numero = None
    if not caiu_no_controle_processos:
        numero = sei_page.extrair_numero_processo(frame, page)

        if not numero:
            numero = sei_page.copiar_numero_processo(page)

        if not numero:
            try:
                numero = frame.text_content(sel["numero_processo_gerado"])
            except Exception:
                numero = None

    if numero:
        numero = numero.strip()

    numero_seguro = (numero or "numero_desconhecido").replace("/", "-")
    sei_page.screenshot(page, f"processo_linha{processo.linha}_apos_salvar_{numero_seguro}")
    sei_page.marcar_tempo(f"linha{processo.linha}: salvou processo")

    if caiu_no_controle_processos and not numero:
        raise RuntimeError(
            f"Depois do Salvar, a linha {processo.linha} caiu na lista 'Controle de Processos' "
            "em vez da tela do processo criado — o processo provavelmente NÃO foi criado de "
            f"verdade. Confira o screenshot processo_linha{processo.linha}_apos_salvar_numero_desconhecido.png "
            "e verifique manualmente no SEI antes de tentar de novo."
        )

    if not numero:
        print(
            f"Processo da linha {processo.linha} foi salvo, mas não consegui ler o número "
            "automaticamente. Confira o screenshot para ver o número gerado."
        )
        return "SALVO-NUMERO-DESCONHECIDO"

    print(f"Processo criado: {numero} (linha {processo.linha})")
    return numero


def atribuir_processo(page: Page, numero_processo: str) -> None:
    """Clica no ícone "Atribuir Processo" da barra de ferramentas do processo.

    Chamado logo após criar o processo, antes de incluir os documentos.
    """
    numero_seguro = numero_processo.replace("/", "-")

    sei_page.clicar_por_texto_ou_icone(page, "Atribuir Processo")
    sei_page.esperar_carregar(page)
    sei_page.marcar_tempo(f"{numero_seguro}: clicou Atribuir Processo")

    frame = sei_page.frame_conteudo(page)
    sei_page.selecionar_select_por_rotulo(frame, "Atribuir para", config.ATRIBUIR_PARA_PADRAO)
    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_atribuir_processo")
    sei_page.marcar_tempo(f"{numero_seguro}: selecionou atribuir para")

    sei_page.clicar_botao(frame, "Salvar")
    sei_page.esperar_carregar(page)
    # Pausa extra (só aqui): o SEI parece demorar mais pra "assentar" logo
    # depois de atribuir o processo — sem isso, a primeira busca do
    # documento seguinte às vezes trava vários segundos esperando o
    # servidor responder.
    page.wait_for_timeout(800)
    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_atribuir_salvar")
    sei_page.marcar_tempo(f"{numero_seguro}: salvou atribuição")


def relacionar_processo(page: Page, numero_processo: str) -> None:
    """Relaciona o processo aberto ao processo de referência fixo (tela
    "Relacionamentos do Processo") — digita o número em "Processo Destino",
    clica em Pesquisar e depois em Adicionar.

    Chamado logo após atribuir o processo, antes de incluir os documentos.
    """
    numero_seguro = numero_processo.replace("/", "-")

    sei_page.clicar_por_texto_ou_icone(page, "Relacionamentos do Processo")
    sei_page.esperar_carregar(page)
    sei_page.marcar_tempo(f"{numero_seguro}: clicou Relacionamentos do Processo")

    frame = sei_page.frame_conteudo(page)
    sei_page.digitar_por_rotulo_ou_seletor(
        frame, "Processo Destino", config.SELECTORS.get("campo_processo_destino", ""),
        config.PROCESSO_RELACIONADO_PADRAO,
    )
    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_digitar_processo_destino")

    sei_page.clicar_botao(frame, "Pesquisar")
    sei_page.esperar_carregar(page)
    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_pesquisar_relacionamento")
    sei_page.marcar_tempo(f"{numero_seguro}: pesquisou processo destino")

    frame = sei_page.frame_conteudo(page)
    sei_page.clicar_botao(frame, "Adicionar")
    sei_page.esperar_carregar(page)
    # Mesma pausa extra que já fazemos depois de atribuir o processo: o SEI
    # demora mais pra "assentar" logo após uma ação de processo, e sem isso
    # a primeira busca do documento seguinte às vezes travava vários
    # segundos esperando o servidor responder.
    page.wait_for_timeout(800)
    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_adicionar_relacionamento")
    sei_page.marcar_tempo(f"{numero_seguro}: adicionou relacionamento")


def sair_do_processo(page: Page, numero_processo: str) -> None:
    """Clica no ícone "Controle de Processos" pra sair da tela do processo
    e voltar pra lista — chamado depois de incluir os 4 documentos, antes
    de seguir pra próxima linha da planilha.
    """
    numero_seguro = numero_processo.replace("/", "-")

    sei_page.clicar_por_texto_ou_icone(page, "Controle de Processos")
    sei_page.esperar_carregar(page)
    sei_page.screenshot(page, f"doc_{numero_seguro}_apos_sair_do_processo")
    sei_page.marcar_tempo(f"{numero_seguro}: saiu do processo")
