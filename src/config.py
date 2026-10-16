"""
Configuração central da automação SEI.

IMPORTANTE: os seletores abaixo são PLACEHOLDERS. Cada instalação do SEI pode
ter pequenas customizações visuais/estruturais. Antes de rodar de verdade,
capture os seletores reais na sua instância do SEI (veja README.md -> "Como
capturar seletores").
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "processos.xlsx"
STATUS_FILE = BASE_DIR / "status" / "processados.json"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
USER_DATA_DIR = BASE_DIR / ".browser-profile"  # perfil persistente do Chrome (mantém sessão logada)

# Data de corte do painel (painel_processos.html): só mostra processos
# criados a partir desta data em diante — fixo, não muda sozinho com o
# tempo. Ajuste aqui se quiser mudar o corte.
PAINEL_DATA_CORTE = "2026-09-22"

SEI_URL = "https://sei.exemplo.gov.br"  # URL real da sua instância vai em config_local.py

# Porta de depuração remota do Chrome que você abre manualmente antes de
# rodar a automação (veja README.md -> "Conectar num Chrome já logado").
CDP_URL = "http://localhost:9222"

# ---------------------------------------------------------------------------
# Seletores da interface do SEI (TODO: capturar via codegen — ver README)
# Mantidos centralizados aqui para facilitar ajuste sem mexer na lógica.
# ---------------------------------------------------------------------------
SELECTORS = {
    # Frame principal de conteúdo do SEI (a tela útil quase sempre fica
    # dentro de um iframe, não direto na page). Ajuste o nome/seletor real.
    "frame_conteudo": "ifrVisualizacao",  # TODO — nome ou seletor do iframe principal

    # Tela inicial / menu
    "menu_iniciar_processo": "text=Iniciar Processo",  # TODO
    # Formulário "Iniciar Processo"
    "campo_tipo_processo": "#selProcedimento",  # TODO
    "campo_especificacao": "#txtDescricao",  # TODO
    "campo_nivel_acesso_publico": "#optPublico",  # TODO
    "campo_nivel_acesso_restrito": "#optRestrito",  # TODO
    "campo_nivel_acesso_sigiloso": "#optSigiloso",  # TODO
    "campo_hipotese_legal": "#selHipoteseLegal",
    "botao_salvar_processo": "#btnSalvar",  # TODO
    # Após salvar: onde aparece o número do processo gerado
    "numero_processo_gerado": ".processo-numero",  # TODO

    # Inclusão de documento
    "menu_incluir_documento": "text=Incluir Documento",  # TODO
    "campo_tipo_documento": "#selSerie",  # TODO
    "campo_descricao_documento": "#txtDescricao",  # TODO
    "campo_nome_arvore": "#txtNomeArvore",  # TODO
    "campo_data_documento": "#txtDataDocumento",  # TODO
    "botao_confirmar_dados_documento": "#btnSalvar",  # TODO

    # Editor de texto rico (geralmente dentro de um iframe)
    "frame_editor": "iframe[id*='ifrEditor']",  # TODO
    "corpo_editor": "body",  # dentro do frame_editor, geralmente <body contenteditable="true">
    "botao_salvar_documento": "#btnSalvar",  # TODO
}

# ---------------------------------------------------------------------------
# Comportamento
# ---------------------------------------------------------------------------
DRY_RUN_DEFAULT = True  # roda apenas 1 processo e para antes de salvar, até você validar
TIMEOUT_PADRAO_MS = 15_000

# Tipo de processo aplicado a todo processo criado (ignora a coluna
# "tipo_processo" da planilha — todos os processos usam este mesmo tipo)
TIPO_PROCESSO_PADRAO = "Pessoal: Despesas de exercícios anteriores"

# Nível de acesso aplicado a todo processo criado: "publico", "restrito" ou "sigiloso"
NIVEL_ACESSO_PADRAO = "restrito"

# Usuário pra quem todo processo criado é atribuído (tela "Atribuir Processo",
# logo após a criação, antes de incluir os documentos)
ATRIBUIR_PARA_PADRAO = "seu.usuario"

# Processo relacionado a todo processo criado (tela "Relacionamentos do
# Processo", logo após atribuir e antes de incluir os documentos)
PROCESSO_RELACIONADO_PADRAO = "00000.000000/0000-00"

# Hipótese legal usada quando o nível de acesso é restrito/sigiloso
# (trecho do texto da opção — não precisa ser igual, só precisa estar contido)
HIPOTESE_LEGAL_PADRAO = "Informação Pessoal"

# Tipo de documento aplicado a todo documento incluído (mesma ideia do
# TIPO_PROCESSO_PADRAO acima) — "Externo" = anexar um arquivo já pronto,
# em vez de gerar um documento nativo do SEI.
TIPO_DOCUMENTO_PADRAO = "Externo"

# Tipo do documento externo (o <select> dentro do formulário "Registrar
# Documento Externo") — texto completo pra não colidir com outras opções
# que contenham um trecho parecido (ex.: "Nota" também casa com "Anotação").
TIPO_DOCUMENTO_EXTERNO_PADRAO = "Anexo"

# Texto do campo "Nome na Árvore" aplicado a todo documento incluído
NOME_ARVORE_PADRAO = "Nota Técnica Nº X/AAAA/UNIDADE"

# Arquivo anexado como Documento Externo
ARQUIVO_ANEXO_PADRAO = BASE_DIR / "src" / "PDFs" / "nota_tecnica.pdf"

# Segundo documento incluído em cada processo (Despacho), criado logo após
# a Nota Técnica acima — mesmos campos (Anexo / Nato-digital / Público),
# só muda o nome na árvore e o arquivo anexado.
NOME_ARVORE_DESPACHO = "Despacho - Plano de Trabalho"
ARQUIVO_ANEXO_DESPACHO = BASE_DIR / "src" / "PDFs" / "despacho_plano_trabalho.pdf"

# Terceiro documento incluído em cada processo (Despacho de Unificação de
# Planilhas), criado logo após o Despacho acima — mesmos campos (Anexo /
# Nato-digital / Público), só muda o nome na árvore e o arquivo anexado.
NOME_ARVORE_UNIFICACAO = "Despacho - Unificação de Planilhas"
ARQUIVO_ANEXO_UNIFICACAO = BASE_DIR / "src" / "PDFs" / "despacho_unificacao.pdf"

# Quarto documento incluído em cada processo (Despacho de Aprovação do Plano
# de Trabalho de Processos), criado logo após o de Unificação acima —
# mesmos campos (Anexo / Nato-digital / Público), só muda o nome na árvore
# e o arquivo anexado.
NOME_ARVORE_APROVACAO = "Despacho - Aprovação do Plano de Trabalho"
ARQUIVO_ANEXO_APROVACAO = BASE_DIR / "src" / "PDFs" / "despacho_aprovacao.pdf"

# ---------------------------------------------------------------------------
# Overrides locais
# ---------------------------------------------------------------------------
# Os valores acima são exemplos genéricos. Dados reais (usuário, números de
# processo, nomes e PDFs dos documentos) ficam em src/config_local.py, que
# não é versionado — veja src/config_local.example.py.
try:
    from .config_local import *  # noqa: F401,F403
except ImportError:
    pass
