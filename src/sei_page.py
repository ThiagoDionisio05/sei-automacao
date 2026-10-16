"""Helpers para navegar na estrutura de frames do SEI."""

import re
import time

from playwright.sync_api import Page, Frame

from . import config

NUMERO_PROCESSO_RE = re.compile(r"\d{5}\.\d{6}/\d{4}-\d{2}")

_ultimo_tempo: float | None = None


def marcar_tempo(rotulo: str) -> None:
    """Imprime quanto tempo passou desde a última chamada a esta função.

    Diagnóstico temporário pra ver onde o tempo está indo em cada etapa —
    chamada em pontos-chave de processo.py e documento.py.
    """
    global _ultimo_tempo
    agora = time.perf_counter()
    if _ultimo_tempo is not None:
        print(f"  [tempo] {rotulo}: {agora - _ultimo_tempo:.1f}s")
    _ultimo_tempo = agora


def extrair_numero_processo(frame, page: Page | None = None) -> str | None:
    """Extrai o número do processo (formato NNNNN.NNNNNN/AAAA-NN) — tenta o
    texto visível primeiro e, se não achar (ex.: número mostrado via CSS ou
    só num atributo/título), tenta o título da aba e o HTML bruto.
    """
    fontes = []

    try:
        fontes.append(frame.locator("body").inner_text())
    except Exception:
        pass

    if page is not None:
        try:
            fontes.append(page.title())
        except Exception:
            pass
        try:
            fontes.append(page.content())
        except Exception:
            pass

    for texto in fontes:
        match = NUMERO_PROCESSO_RE.search(texto or "")
        if match:
            return match.group(0)

    return None


def esta_em_controle_processos(page: Page) -> bool:
    """Detecta se a página atual é a lista "Controle de Processos" (tela
    de listagem, não a tela de um processo específico) — se o Salvar cair
    aqui, provavelmente não criou o processo de verdade.
    """
    try:
        return page.get_by_text("Controle de Processos", exact=True).first.is_visible()
    except Exception:
        return False


def detectar_pagina_erro(page: Page) -> str | None:
    """Detecta se o SEI mostrou uma página de erro genérica do sistema
    (título "Erro" + mensagem em vermelho, ex.: "Erro processando operação
    gerarRN0154"). Retorna a mensagem de erro, se achar.
    """
    try:
        titulo = page.get_by_role("heading", name="Erro", exact=True)
        if titulo.count() == 0 or not titulo.first.is_visible():
            return None
    except Exception:
        return None

    try:
        corpo = page.locator("body").inner_text()
    except Exception:
        return "Erro (não consegui ler a mensagem detalhada)."

    linhas = [l.strip() for l in corpo.splitlines() if l.strip()]
    for linha in linhas:
        if linha.lower().startswith("erro") and linha.lower() != "erro":
            return linha
    return "Erro (mensagem detalhada não identificada — confira o screenshot)."


def procurar_mensagem_erro(frame) -> str | None:
    """Procura mensagens de erro/validação visíveis na tela (ex.: campo
    obrigatório não preenchido) para diagnosticar por que o Salvar não
    completou como esperado.
    """
    seletores_erro = [
        ".infraAvisoErro",
        ".alert-danger",
        "#divInfraAvisoErro",
        "[class*='erro' i]",
        "[class*='error' i]",
    ]
    for seletor in seletores_erro:
        try:
            loc = frame.locator(seletor)
            if loc.count() > 0 and loc.first.is_visible():
                texto = loc.first.inner_text().strip()
                if texto:
                    return texto
        except Exception:
            continue
    return None


def frame_conteudo(page: Page) -> Frame:
    """Retorna o frame principal onde os formulários do SEI são renderizados.

    O SEI organiza a tela em frames (menu, árvore, conteúdo). A maior parte
    dos formulários fica no frame de conteúdo. Ajuste o seletor em
    config.SELECTORS['frame_conteudo'] conforme a instância real.
    """
    nome = config.SELECTORS["frame_conteudo"]
    frame = page.frame(name=nome)
    if frame is None:
        # fallback: tenta localizar por seletor CSS caso não seja um "name"
        handle = page.query_selector(f"iframe[name='{nome}'], {nome}")
        if handle:
            frame = handle.content_frame()
    if frame is None:
        outros_frames = [f for f in page.frames if f != page.main_frame]
        if not outros_frames:
            # Esta tela não usa iframe — o formulário está direto na página.
            print(f"(Sem iframes nesta tela — usando a página principal em vez de '{nome}'.)")
            return page.main_frame
        print(f"\nFrames disponíveis na página (procurando por '{nome}'):")
        for f in page.frames:
            print(f"  name={f.name!r}  url={f.url!r}")
        raise RuntimeError(
            f"Não encontrei o frame de conteúdo ('{nome}'). "
            "Ajuste config.SELECTORS['frame_conteudo']."
        )
    return frame


def clicar_por_texto_ou_icone(page: Page, texto: str) -> None:
    """Clica em um item de menu localizando-o pelo texto visível ou, se não
    achar, pelo ícone associado (img/title/aria-label com o mesmo texto).

    Procura em TODOS os frames da página (o SEI costuma colocar barras de
    ferramentas dentro de iframes separados do conteúdo principal), não só
    na página de topo.
    """
    for fr in page.frames:
        candidatos = [
            fr.get_by_text(texto, exact=True),
            fr.locator(f"a:has-text('{texto}')"),
            fr.locator(f"img[alt='{texto}'], img[title='{texto}']"),
            fr.locator(f"[title='{texto}']"),
            # correspondência parcial, sem diferenciar maiúsculas/minúsculas —
            # cobre título com sufixo (atalho de teclado, etc.)
            fr.get_by_text(texto, exact=False),
            fr.locator(f"[title*='{texto}' i]"),
            fr.locator(f"[aria-label*='{texto}' i]"),
            fr.locator(f"img[alt*='{texto}' i]"),
        ]
        for loc in candidatos:
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    return
            except Exception:
                continue

    # Diagnóstico: lista elementos com title/aria-label/alt em todos os frames.
    print(f"\nNão encontrei '{texto}'. Elementos com title/aria-label/alt encontrados:")
    for fr in page.frames:
        try:
            candidatos_titulo = fr.locator("[title], [aria-label], img[alt]")
            total = candidatos_titulo.count()
        except Exception:
            continue
        for i in range(min(total, 80)):
            item = candidatos_titulo.nth(i)
            try:
                if item.is_visible():
                    titulo = (
                        item.get_attribute("title")
                        or item.get_attribute("aria-label")
                        or item.get_attribute("alt")
                        or ""
                    )
                    if titulo.strip():
                        print(f"  [frame={fr.url}] {titulo!r}")
            except Exception:
                continue

    raise RuntimeError(
        f"Não encontrei elemento clicável para '{texto}' (nem por texto, nem por ícone)."
    )


def buscar_e_selecionar(frame, texto: str, timeout_ms: int = 8000) -> None:
    """Digita `texto` no campo de busca visível da tela e clica no item da
    lista de resultados que corresponde exatamente a esse texto.

    Usado em telas do SEI que são um campo de filtro + lista clicável
    (ex.: "Escolha o Tipo do Processo"), em vez de um <select> tradicional.
    """
    campo_busca = frame.locator("input[type='text'], input:not([type])").first
    campo_busca.fill(texto)
    item = frame.get_by_text(texto, exact=True).first
    item.wait_for(state="visible", timeout=timeout_ms)
    item.click()


def documento_existe_na_arvore(page: Page, texto: str, timeout_ms: int = 4000) -> bool:
    """Verifica se já existe, na árvore do processo atualmente aberto, um
    documento cujo nome contenha `texto` (comparação parcial, ignorando
    maiúsculas/minúsculas e diferenças de espaço — inclusive o espaço
    não separável que o SEI costuma usar nos rótulos da árvore, que quebra
    uma comparação de texto simples).

    Restrito aos links (<a>) da página — os itens da árvore são sempre
    links — em vez do texto inteiro do body: usar o body inteiro dava falso
    positivo com o conteúdo do PDF exibido na tela de visualização do
    documento (o texto do PDF entra no innerText da página e podia bater
    com o nome de outro documento que ainda não existia).

    Usado para não recriar um documento que já foi incluído antes. Procura
    em todos os frames (a árvore normalmente fica num iframe separado do
    conteúdo principal) e tenta algumas vezes, já que a árvore pode
    carregar de forma assíncrona.

    Compara só os primeiros 35 caracteres de `texto`: o SEI parece truncar
    nomes longos no "Nome na Árvore" (confirmado — nomes com mais de ~50
    caracteres não batiam com o texto completo, mesmo com o documento
    visivelmente salvo na árvore). 35 caracteres já é suficiente pra
    distinguir os documentos usados neste projeto entre si.
    """
    alvo = re.sub(r"\s+", " ", texto).strip().lower()[:35]
    tentativas = max(1, timeout_ms // 400)

    for _ in range(tentativas):
        for fr in page.frames:
            try:
                links = fr.locator("a")
                candidatos = links.all_inner_texts()
                candidatos += links.evaluate_all(
                    "els => els.map(e => e.getAttribute('title') || '')"
                )
            except Exception:
                continue
            for candidato in candidatos:
                if alvo in re.sub(r"\s+", " ", candidato).strip().lower():
                    return True
        page.wait_for_timeout(400)

    return False


def anexar_arquivo(frame, caminho_arquivo, timeout_ms: int = 8000, tentativas_upload: int = 3) -> bool:
    """Anexa um arquivo direto no <input type="file"> escondido atrás do
    botão "Anexar Arquivo..." — não precisa clicar no botão nem interagir
    com a janela nativa do sistema, é bem mais rápido e confiável.

    Depois de setar o arquivo, ESPERA a "Lista de Anexos" mostrar de fato
    1+ registro antes de retornar True — o SEI registra o anexo na lista
    de forma assíncrona (JS), e sem essa confirmação o código seguia pro
    Salvar rápido demais às vezes, salvando o documento sem arquivo
    nenhum anexado (confirmado: "Lista de Anexos (0 registros)" mesmo
    depois do set_input_files não ter dado erro).

    Faz até `tentativas_upload` rodadas completas (seta o arquivo de novo
    a cada rodada) antes de desistir — a confirmação às vezes falha por
    lentidão pontual do SEI, não por erro real, e uma nova tentativa
    costuma resolver.
    """
    padrao = re.compile(r"Lista de Anexos\s*\((\d+)\s*registros?\)", re.IGNORECASE)

    for _ in range(tentativas_upload):
        try:
            campo = frame.locator("input[type='file']").first
            campo.set_input_files(str(caminho_arquivo), timeout=timeout_ms)
        except Exception:
            continue

        tentativas_espera = max(1, timeout_ms // 300)
        for _ in range(tentativas_espera):
            try:
                texto = frame.get_by_text(padrao).first.inner_text()
                m = padrao.search(texto)
                if m and int(m.group(1)) > 0:
                    return True
            except Exception:
                pass
            frame.wait_for_timeout(300)

    return False


def selecionar_select_por_rotulo(frame, rotulo: str, texto: str, timeout_ms: int = 5000) -> bool:
    """Seleciona, num <select> nativo achado pelo rótulo visível, a opção
    cujo texto contém `texto` (não precisa ser igual). Faz polling porque
    as opções desse tipo de campo no SEI às vezes carregam via AJAX depois
    do campo já estar visível. Retorna True se conseguiu selecionar.
    """
    try:
        campo = frame.get_by_label(rotulo, exact=False)
        campo.wait_for(state="visible", timeout=timeout_ms)
    except Exception:
        return False

    correspondente = None
    tentativas = max(1, timeout_ms // 300)
    for _ in range(tentativas):
        try:
            opcoes = campo.locator("option").all_inner_texts()
        except Exception:
            opcoes = []
        correspondente = next((o for o in opcoes if texto.lower() in o.lower()), None)
        if correspondente:
            break
        frame.wait_for_timeout(300)

    if not correspondente:
        try:
            todas = campo.locator("option").all_inner_texts()
        except Exception:
            todas = []
        primeiro_termo = texto.split()[0].lower() if texto.split() else texto.lower()
        parecidas = [o for o in todas if primeiro_termo in o.lower()]
        print(f"\nNão achei opção contendo '{texto}' em '{rotulo}'.")
        if parecidas:
            print(f"Opções parecidas (contêm '{primeiro_termo}'): {parecidas}")
        else:
            print(f"Nenhuma opção contém '{primeiro_termo}'. Todas as opções: {todas}")
        return False

    try:
        campo.select_option(label=correspondente)
        return True
    except Exception:
        return False


def marcar_radio(frame, rotulo: str, timeout_ms: int = 2000) -> bool:
    """Marca um radio button pelo rótulo visível, direto com força (esses
    campos do SEI raramente passam na checagem normal de visibilidade, então
    a tentativa "normal" só perde tempo). Retorna True se conseguiu marcar.
    """
    try:
        frame.get_by_label(rotulo, exact=True).check(timeout=timeout_ms, force=True)
        return True
    except Exception:
        return False


def preencher_campo_apos_radio(frame, rotulo_radio: str, texto: str, timeout_ms: int = 3000) -> bool:
    """Preenche o campo de texto que aparece logo ao lado/depois de um radio
    (ex.: a caixa de número do documento modelo, que fica ao lado do radio
    "Documento Modelo"). Retorna True se achou e preencheu.
    """
    try:
        radio = frame.get_by_label(rotulo_radio, exact=True)
        campo = radio.locator("xpath=following::input[@type='text'][1]")
        campo.fill(texto, timeout=timeout_ms)
        return True
    except Exception:
        return False


def clicar_botao(frame, texto: str, timeout_ms: int = 8000) -> None:
    """Clica num botão pelo texto/rótulo visível (ex.: "Salvar").

    A tela pode ter mais de um elemento com esse texto (cópia fixa no topo
    + botão real embaixo, por exemplo) — em vez de confiar cegamente no
    primeiro (`.first`), procura especificamente um que esteja visível.
    """
    candidatos = [
        frame.get_by_role("button", name=texto, exact=True),
        frame.get_by_text(texto, exact=True),
    ]
    for loc in candidatos:
        try:
            total = loc.count()
        except Exception:
            continue
        for i in range(total):
            item = loc.nth(i)
            try:
                if item.is_visible():
                    item.click(timeout=timeout_ms)
                    return
            except Exception:
                continue

    raise RuntimeError(f"Não encontrei nenhum botão visível com o texto '{texto}'.")


def preencher_por_rotulo_ou_seletor(frame, rotulo: str, seletor: str, texto: str) -> None:
    """Preenche um campo de texto/textarea, localizando primeiro pelo
    rótulo visível na tela e, se não achar, pelo seletor configurado.

    Usa `force=True` e um timeout curto pra não ficar parado nas checagens
    de actionability do Playwright (visível/estável/etc.) — o campo já está
    na tela nesse ponto do fluxo, então isso só economiza tempo sem trocar
    de comportamento.
    """
    try:
        frame.get_by_label(rotulo, exact=False).fill(texto, timeout=3000, force=True)
        return
    except Exception:
        pass
    frame.fill(seletor, texto, timeout=3000, force=True)


def digitar_por_rotulo_ou_seletor(
    frame, rotulo: str, seletor: str, texto: str, delay: int = 5
) -> bool:
    """Digita um texto tecla por tecla (não usa .fill()) num campo achado
    pelo rótulo visível, com fallback pro seletor configurado. Necessário
    para campos com máscara/validação em JS (ex.: data), que costumam não
    reagir a um .fill() direto — só a eventos reais de teclado.
    Retorna True se conseguiu.
    """
    try:
        campo = frame.get_by_label(rotulo, exact=False)
        campo.click()
        campo.press_sequentially(texto, delay=delay)
        return True
    except Exception:
        pass

    try:
        campo = frame.locator(seletor)
        campo.click()
        campo.press_sequentially(texto, delay=delay)
        return True
    except Exception:
        return False


def selecionar_nivel_acesso(frame, nivel: str) -> None:
    """Marca o rádio de Nível de Acesso do processo e CONFIRMA que marcou.

    `nivel` é "publico", "restrito" ou "sigiloso". Tenta várias estratégias
    e, ao final, verifica de fato o estado do rádio — se nenhuma estratégia
    realmente marcou o campo, mostra um diagnóstico de todos os rádios da
    tela em vez de seguir em frente silenciosamente.
    """
    rotulo = nivel.capitalize()
    erros = []

    def esta_marcado() -> bool:
        try:
            return frame.get_by_label(rotulo, exact=True).is_checked()
        except Exception:
            return False

    chave = f"campo_nivel_acesso_{nivel}"
    seletor = config.SELECTORS.get(chave)

    # O rádio real costuma ficar visualmente escondido atrás do estilo
    # customizado do SEI — a tentativa sem force quase sempre falha (só
    # depois de esperar o timeout inteiro). Por isso o force=True vai
    # primeiro, como caminho rápido; as outras ficam só de fallback.
    tentativas = [
        ("get_by_label (force)", lambda: frame.get_by_label(rotulo, exact=True).check(timeout=2000, force=True)),
        ("get_by_label", lambda: frame.get_by_label(rotulo, exact=True).check(timeout=2000)),
    ]
    if seletor:
        tentativas.append((f"seletor {seletor} (force)", lambda: frame.locator(seletor).first.check(timeout=2000, force=True)))
        tentativas.append((f"seletor {seletor}", lambda: frame.locator(seletor).first.check(timeout=2000)))

    for nome_tentativa, fn in tentativas:
        try:
            fn()
        except Exception as e:
            erros.append(f"{nome_tentativa}: {e}")
            continue
        if esta_marcado():
            return

    # Diagnóstico: lista os rádios da tela para achar o certo.
    radios = frame.locator("input[type='radio']")
    total = radios.count()
    print(f"\nNão consegui marcar '{rotulo}' no Nível de Acesso. Tentativas:")
    for e in erros:
        print(f"  - {e}")
    if total:
        print("Rádios encontrados na tela:")
        for i in range(total):
            r = radios.nth(i)
            try:
                rid = r.get_attribute("id") or ""
                rname = r.get_attribute("name") or ""
                rvalue = r.get_attribute("value") or ""
                checked = r.is_checked()
                print(f"  id={rid!r} name={rname!r} value={rvalue!r} checked={checked}")
            except Exception:
                continue
    else:
        print("Nenhum input[type=radio] encontrado na tela.")

    raise RuntimeError(
        f"Não consegui marcar o nível de acesso '{rotulo}'. Veja a lista de rádios acima "
        "e ajuste config.SELECTORS['campo_nivel_acesso_" + nivel + "']."
    )


def selecionar_hipotese_legal(frame, texto: str, timeout_ms: int = 5000) -> None:
    """Seleciona a Hipótese Legal (campo <select> que aparece quando o
    nível de acesso é Restrito ou Sigiloso). `texto` casa por trecho
    contido na opção (ex.: "Informação Pessoal" casa com "Informação
    Pessoal (Art. 31 da Lei nº 12.527/2011)").
    """
    seletor = config.SELECTORS.get("campo_hipotese_legal")
    if seletor:
        try:
            loc = frame.locator(seletor)
            loc.wait_for(state="visible", timeout=timeout_ms)

            # As opções desse <select> são carregadas via AJAX depois que o
            # campo já está visível — espera até a opção aparecer, não só
            # até o campo aparecer.
            correspondente = None
            tentativas = max(1, timeout_ms // 300)
            for _ in range(tentativas):
                opcoes = loc.locator("option").all_inner_texts()
                correspondente = next((o for o in opcoes if texto.lower() in o.lower()), None)
                if correspondente:
                    break
                frame.wait_for_timeout(300)

            if correspondente:
                frame.select_option(seletor, label=correspondente)
                return
        except Exception:
            pass

    # Diagnóstico: lista os <select> visíveis na tela para achar o campo certo.
    selects = frame.locator("select")
    total = selects.count()
    print(f"\nNão consegui selecionar '{texto}' com o seletor {seletor!r}.")
    if total:
        print("Campos <select> encontrados na tela:")
        for i in range(total):
            item = selects.nth(i)
            try:
                sid = item.get_attribute("id") or ""
                sname = item.get_attribute("name") or ""
                opcoes = item.locator("option").all_inner_texts()
                print(f"  id={sid!r} name={sname!r} opcoes={opcoes}")
            except Exception:
                continue
    else:
        print("Nenhum <select> visível na tela.")

    raise RuntimeError(
        f"Não encontrei a Hipótese Legal '{texto}'. Ajuste "
        "config.SELECTORS['campo_hipotese_legal'] com o id certo (veja lista acima)."
    )


def copiar_numero_processo(page: Page, timeout_ms: int = 5000) -> str | None:
    """Usa o recurso nativo do SEI "Copiar Número do Processo" para pegar o
    número do processo recém-criado via clipboard (mais confiável do que
    tentar ler o número direto de um elemento da tela).

    Retorna None se não achar o botão/ícone ou se o clipboard vier vazio.
    """
    candidatos = [
        page.get_by_title("Copiar Número do Processo", exact=False),
        page.get_by_role("link", name="Copiar Número do Processo", exact=False),
        page.locator("[title*='Copiar Número' i]"),
        page.locator("a[onclick*='Copiar' i]"),
    ]

    for loc in candidatos:
        try:
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.click(timeout=timeout_ms)
                break
        except Exception:
            continue
    else:
        return None

    page.wait_for_timeout(300)
    try:
        texto = page.evaluate("() => navigator.clipboard.readText()")
    except Exception:
        return None

    texto = (texto or "").strip()
    return texto or None


def screenshot(page: Page, nome: str) -> None:
    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    caminho = config.SCREENSHOTS_DIR / f"{nome}.png"
    page.screenshot(path=str(caminho), full_page=True)


def esperar_carregar(page: Page, timeout_ms: int = 2_500) -> None:
    """Espera a página "assentar" após uma navegação/ação, sem travar.

    O SEI mantém requisições de fundo (polling/heartbeat) que quase nunca
    deixam a rede ficar totalmente ociosa — por isso `networkidle` quase
    sempre estoura o timeout mesmo com a tela já pronta para uso. Por isso o
    timeout aqui é bem curto: só serve pra pegar de graça os casos em que a
    rede realmente fica ociosa rápido; no caso comum (não fica), cai direto
    na pausa fixa pequena em vez de ficar parado esperando à toa.
    """
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        page.wait_for_timeout(800)
