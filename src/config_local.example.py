"""
Modelo de configuração local.

Copie este arquivo para `src/config_local.py` e preencha com seus dados
reais. O `config_local.py` está no .gitignore — nunca é versionado — e
sobrescreve os valores de exemplo de `src/config.py`.
"""

from pathlib import Path

_PDFS = Path(__file__).resolve().parent / "PDFs"

# Endereço da sua instância do SEI
SEI_URL = "https://sei.seuorgao.gov.br"

# Usuário do SEI para quem cada processo criado é atribuído
ATRIBUIR_PARA_PADRAO = "seu.usuario"

# Processo de referência relacionado a todo processo criado
PROCESSO_RELACIONADO_PADRAO = "00000.000000/0000-00"

# Documentos anexados (nome na árvore + arquivo PDF)
NOME_ARVORE_PADRAO = "Nota Técnica Nº X/AAAA/UNIDADE"
ARQUIVO_ANEXO_PADRAO = _PDFS / "nota_tecnica.pdf"

NOME_ARVORE_DESPACHO = "Despacho - Plano de Trabalho"
ARQUIVO_ANEXO_DESPACHO = _PDFS / "despacho_plano_trabalho.pdf"

NOME_ARVORE_UNIFICACAO = "Despacho - Unificação de Planilhas"
ARQUIVO_ANEXO_UNIFICACAO = _PDFS / "despacho_unificacao.pdf"

NOME_ARVORE_APROVACAO = "Despacho - Aprovação do Plano de Trabalho"
ARQUIVO_ANEXO_APROVACAO = _PDFS / "despacho_aprovacao.pdf"
