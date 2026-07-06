"""Relatórios PDF (fpdf2) com a identidade visual do protótipo.

Identidade: cabeçalho ferro (IRON) com marca + título em laranja (WELD), rótulos de
seção em WELD_D, valores em Courier (mono), chips de origem coloridos, caixa de
total escura e rodapé fino. TODO texto passa por L() (sanitização latin-1).
"""

import os
import re
import unicodedata
from decimal import Decimal

from fpdf import FPDF

from app.config import settings
from app.utils import data_br, data_curta, horas_fmt, moeda

# ---- Cores do protótipo (RGB) ----
IRON = (28, 36, 44)
IRON2 = (36, 46, 56)
INK = (22, 28, 34)
SLATE = (90, 102, 114)
SLATE2 = (139, 149, 160)
LINE = (221, 227, 232)
SURF2 = (244, 246, 248)
WELD = (224, 90, 0)
WELD_D = (184, 74, 2)
WELD_SOFT = (253, 238, 226)
IN_GREEN = (23, 143, 82)
IN_SOFT = (227, 244, 234)
PASS_BLUE = (47, 107, 176)
PASS_SOFT = (231, 239, 248)
POCKET_RED = (194, 58, 46)
POCKET_SOFT = (251, 233, 231)
WARN = (183, 121, 31)
WARN_SOFT = (253, 243, 224)

PAGE_W = 210
MARGIN = 14
CONTENT_W = PAGE_W - 2 * MARGIN
QUEBRA_Y = 268  # limiar para quebra de página manual em desenhos custom

# Estilos de chip: (cor do texto, fundo suave)
CHIP = {
    "pass": (PASS_BLUE, PASS_SOFT),
    "pocket": (POCKET_RED, POCKET_SOFT),
    "warn": (WARN, WARN_SOFT),
    "in": (IN_GREEN, IN_SOFT),
    "neutral": (SLATE, SURF2),
}
ORIGEM_CHIP = {
    "repasse": ("Repasse EPR", "pass"),
    "epr_direto": ("EPR direto", "pass"),
    "bolso": ("Do bolso", "pocket"),
    "proprio": ("Empreita", "neutral"),  # "Eu trabalhei" (Dirceu, sem valor)
}
CATEGORIA_LABEL = {
    "deslocamento": "Deslocamento",
    "alimentacao": "Alimentação",
    "material": "Material",
    "outros": "Outros",
}
STATUS_LABEL = {"andamento": "Em andamento", "finalizada": "Finalizada", "fechada": "Fechada"}

# Substituições de caracteres fora do latin-1 (evita '?' feios).
_TROCAS = {
    "—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "→": "->", "−": "-", "•": "-",
}


def L(texto) -> str:
    """Sanitiza QUALQUER texto para latin-1 (fontes core do PDF)."""
    s = str(texto if texto is not None else "")
    for k, v in _TROCAS.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def slug(texto: str) -> str:
    """Nome de arquivo: 'Jato E120' -> 'jato-e120'."""
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "relatorio"


class DirceuPDF(FPDF):
    """Base com cabeçalho ferro + marca, e rodapé fino com paginação."""

    def __init__(self, config, titulo: str, sub: str = "", rodape_id: str = ""):
        super().__init__("P", "mm", "A4")
        self.cfg = config
        self.titulo = titulo
        self.sub = sub
        self.rodape_id = rodape_id
        self.alias_nb_pages()
        self.set_margins(MARGIN, 34, MARGIN)
        self.set_auto_page_break(True, margin=20)
        self.add_page()

    # -- cabeçalho: faixa IRON com marca à esquerda e título/período à direita --
    def header(self):
        self.set_fill_color(*IRON)
        self.rect(0, 0, PAGE_W, 26, style="F")
        x = MARGIN
        logo = getattr(self.cfg, "logo_filename", None)
        if logo:
            caminho = os.path.join(settings.MEDIA_DIR, logo)
            if os.path.isfile(caminho):
                try:
                    self.image(caminho, x=MARGIN, y=6, h=14)
                    x += 20
                except Exception:
                    pass
        else:
            # Losango laranja (motivo do protótipo) como marca padrão.
            self._losango(x + 3, 13, 3)
            x += 9
        self.set_text_color(255, 255, 255)
        self.set_font("helvetica", "B", 12)
        self.set_xy(x, 7)
        self.cell(105, 7, L(self.cfg.nome_exibicao))
        self.set_font("helvetica", "", 7)
        self.set_text_color(*SLATE2)
        self.set_xy(x, 14)
        self.cell(105, 5, L(getattr(self.cfg, "telefone", None) or ""))
        # Título do relatório (WELD, maiúsculas) + identificador/período (branco).
        self.set_font("helvetica", "B", 8)
        self.set_text_color(*WELD)
        self.set_xy(PAGE_W - MARGIN - 100, 6.5)
        self.cell(100, 5, L(self.titulo.upper()), align="R")
        self.set_font("helvetica", "", 9.5)
        self.set_text_color(255, 255, 255)
        self.set_xy(PAGE_W - MARGIN - 120, 12.5)
        self.cell(120, 6, L(self.sub), align="R")
        self.set_y(34)
        self.set_text_color(*INK)

    def footer(self):
        self.set_y(-14)
        y = self.get_y()
        self.set_draw_color(*LINE)
        self.set_line_width(0.3)
        self.line(MARGIN, y, PAGE_W - MARGIN, y)
        self.set_font("helvetica", "", 7)
        self.set_text_color(*SLATE2)
        self.set_xy(MARGIN, y + 1.5)
        self.cell(90, 5, L(self.cfg.nome_exibicao))
        self.set_xy(PAGE_W - MARGIN - 90, y + 1.5)
        direita = (self.rodape_id + " . " if self.rodape_id else "") + f"Página {self.page_no()}/{{nb}}"
        self.cell(90, 5, L(direita), align="R")

    def _losango(self, cx: float, cy: float, r: float, cor=WELD):
        self.set_fill_color(*cor)
        try:
            self.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], style="F")
        except Exception:
            self.rect(cx - r / 1.5, cy - r / 1.5, r * 1.4, r * 1.4, style="F")

    def quebra_se_preciso(self, altura: float = 8):
        if self.get_y() + altura > QUEBRA_Y + 10:
            self.add_page()


# ---------- blocos visuais reutilizáveis ----------

def _sec(pdf: DirceuPDF, texto: str):
    """Rótulo de seção: maiúsculas pequenas em WELD_D."""
    pdf.quebra_se_preciso(14)
    pdf.ln(2.5)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*WELD_D)
    pdf.cell(0, 5, L(texto.upper()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)


def _chip(pdf: DirceuPDF, x: float, y: float, texto: str, estilo: str, h: float = 4.6) -> float:
    """Chip arredondado com fundo suave; retorna a largura desenhada."""
    cor, soft = CHIP[estilo]
    pdf.set_font("helvetica", "B", 6.5)
    w = pdf.get_string_width(L(texto)) + 5
    pdf.set_fill_color(*soft)
    pdf.rect(x, y, w, h, style="F", round_corners=True, corner_radius=1.6)
    pdf.set_text_color(*cor)
    pdf.set_xy(x, y)
    pdf.cell(w, h, L(texto), align="C")
    pdf.set_text_color(*INK)
    return w


def _total_box(pdf: DirceuPDF, rotulo: str, valor_txt: str, h: float = 13, cor=IRON):
    """Caixa escura de total: rótulo à esquerda, valor grande mono à direita."""
    pdf.quebra_se_preciso(h + 4)
    pdf.ln(1.5)
    y = pdf.get_y()
    pdf.set_fill_color(*cor)
    pdf.rect(MARGIN, y, CONTENT_W, h, style="F", round_corners=True, corner_radius=2)
    pdf._losango(MARGIN + 6, y + h / 2, 1.6)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_xy(MARGIN + 10, y)
    pdf.cell(95, h, L(rotulo.upper()))
    pdf.set_font("courier", "B", 14)
    pdf.set_xy(MARGIN, y)
    pdf.cell(CONTENT_W - 6, h, L(valor_txt), align="R")
    pdf.set_y(y + h + 3)
    pdf.set_text_color(*INK)


def _tab_header(pdf: DirceuPDF, cols: list[tuple[str, float, str]]):
    """Cabeçalho de tabela: sem fundo, borda inferior IRON mais grossa."""
    pdf.quebra_se_preciso(10)
    y = pdf.get_y()
    pdf.set_font("helvetica", "B", 7)
    pdf.set_text_color(*SLATE)
    x = MARGIN
    for label, w, align in cols:
        pdf.set_xy(x, y)
        pdf.cell(w, 5.5, L(label.upper()), align=align)
        x += w
    y2 = y + 5.5
    pdf.set_draw_color(*IRON)
    pdf.set_line_width(0.45)
    pdf.line(MARGIN, y2, MARGIN + sum(w for _, w, _ in cols), y2)
    pdf.set_y(y2 + 1)
    pdf.set_text_color(*INK)


def _linha_fina(pdf: DirceuPDF, largura: float = CONTENT_W):
    y = pdf.get_y()
    pdf.set_draw_color(*LINE)
    pdf.set_line_width(0.2)
    pdf.line(MARGIN, y, MARGIN + largura, y)
    pdf.set_y(y + 0.8)


def _nada(pdf: DirceuPDF, texto: str):
    pdf.set_font("helvetica", "I", 8.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 7, L(texto), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)


def _nota(pdf: DirceuPDF, texto: str):
    pdf.ln(1.5)
    pdf.set_font("helvetica", "I", 7.5)
    pdf.set_text_color(*SLATE)
    pdf.multi_cell(CONTENT_W, 4, L(texto))
    pdf.set_text_color(*INK)


# ==================== 1) Dossiê da máquina ====================

def pdf_maquina(config, maquina, entradas, ag, margem, pct) -> DirceuPDF:
    """entradas: DiarioEntrada em ordem ASC; ag: Agregados (custo do Dirceu × EPR)."""
    pdf = DirceuPDF(
        config,
        "Relatório da máquina",
        f"{maquina.nome} - {maquina.cliente}",
        rodape_id=f"Máquina: {maquina.nome}",
    )

    # ---- grade de metadados (3 x 2) ----
    fim = data_br(maquina.data_finalizacao) if maquina.data_finalizacao else "em aberto"
    meta = [
        ("EMPREITA", f"R$ {moeda(maquina.empreita)}", INK, True),
        ("SEU CUSTO", f"R$ {moeda(ag.custo_dirceu)}", INK, True),
        ("MARGEM", f"R$ {moeda(margem)}", IN_GREEN if margem >= 0 else POCKET_RED, True),
        ("HORAS", f"{horas_fmt(ag.horas)}h", INK, True),
        ("STATUS", STATUS_LABEL.get(maquina.status, maquina.status), INK, False),
        ("PERÍODO", f"{data_br(maquina.data_inicio)} -> {fim}", INK, False),
    ]
    col_w = CONTENT_W / 3
    y0 = pdf.get_y()
    for i, (rotulo, valor, cor, mono) in enumerate(meta):
        cx = MARGIN + (i % 3) * col_w
        cy = y0 + (i // 3) * 13
        pdf.set_xy(cx, cy)
        pdf.set_font("helvetica", "B", 6.5)
        pdf.set_text_color(*SLATE2)
        pdf.cell(col_w, 4, L(rotulo))
        pdf.set_xy(cx, cy + 4)
        pdf.set_font("courier" if mono else "helvetica", "B", 10.5)
        pdf.set_text_color(*cor)
        pdf.cell(col_w, 6, L(valor))
    pdf.set_text_color(*INK)
    pdf.set_y(y0 + 27)
    # Detalhe do custo do Dirceu e o que a EPR pagou (fora da margem).
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*SLATE)
    if ag.despesas > 0:
        pdf.cell(0, 4.5, L(
            f"Seu custo: diárias do bolso R$ {moeda(ag.bolso_diarias)}"
            f" + despesas R$ {moeda(ag.despesas)}"
        ), new_x="LMARGIN", new_y="NEXT")
    if ag.custo_epr > 0:
        pdf.cell(0, 4.5, L(
            f"Pago pela EPR (fora da margem): R$ {moeda(ag.custo_epr)}"
            f" - repasse R$ {moeda(ag.repasse)} . direto R$ {moeda(ag.epr_direto)}"
        ), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    pdf.ln(1)
    _linha_fina(pdf)

    # ---- diário em ordem cronológica (leitura tipo história) ----
    _render_diario(pdf, entradas)

    # ---- totais ----
    _total_box(pdf, "Seu custo total", f"R$ {moeda(ag.custo_dirceu)}")
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*SLATE)
    pdf.write(5, L(f"Empreita R$ {moeda(maquina.empreita)} - seu custo R$ {moeda(ag.custo_dirceu)} = margem "))
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(*(IN_GREEN if margem >= 0 else POCKET_RED))
    pdf.write(5, L(f"R$ {moeda(margem)}"))
    pdf.set_text_color(*SLATE)
    pdf.set_font("helvetica", "", 8.5)
    pdf.write(5, L(f"  ({pct}% da empreita consumido)"))
    pdf.set_text_color(*INK)
    pdf.ln(6)
    return pdf


def _render_diario(pdf: DirceuPDF, entradas) -> None:
    """Timeline do diário (reusada por máquina e serviço)."""
    _sec(pdf, "Diário de obra")
    if not entradas:
        _nada(pdf, "Nenhum lançamento no diário.")
    for e in entradas:
        pdf.quebra_se_preciso(16)
        pdf._losango(MARGIN + 1.5, pdf.get_y() + 2.6, 1.3)
        pdf.set_xy(MARGIN + 5, pdf.get_y())
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(40, 5.5, L(data_br(e.data)), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(MARGIN + 5)
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_text_color(*SLATE)
        pdf.multi_cell(CONTENT_W - 5, 4.2, L(e.descricao))
        pdf.set_text_color(*INK)
        pdf.ln(0.6)
        for t in sorted(e.trabalhos, key=lambda x: x.id):
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_xy(MARGIN + 5, y)
            pdf.set_font("helvetica", "", 8.5)
            pdf.cell(58, 5, L(t.ajudante_nome))
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN + 63, y)
            pdf.cell(16, 5, L(f"{horas_fmt(t.horas)}h"), align="R")
            rotulo, estilo = ORIGEM_CHIP.get(t.origem, (t.origem, "pass"))
            _chip(pdf, MARGIN + 84, y + 0.2, rotulo, estilo)
            if not getattr(t, "proprio", False):
                pdf.set_font("courier", "", 9)
                pdf.set_xy(PAGE_W - MARGIN - 30, y)
                pdf.cell(30, 5, L(f"R$ {moeda(t.valor)}"), align="R")
            pdf.set_y(y + 5.4)
        pdf.ln(1)
        _linha_fina(pdf)
        pdf.ln(1)


# ==================== 1b) Dossiê do serviço avulso ====================

def pdf_servico(config, servico, entradas, ag, resultado, pct) -> DirceuPDF:
    """Análogo ao dossiê da máquina: VALOR | SEU CUSTO | RESULTADO | HORAS + diário."""
    pdf = DirceuPDF(
        config, "Relatório do serviço",
        f"{servico.descricao}" + (f" - {servico.cliente}" if servico.cliente else ""),
        rodape_id=f"Serviço: {servico.descricao[:30]}",
    )
    fim = data_br(servico.data_finalizacao) if servico.data_finalizacao else "em aberto"
    meta = [
        ("VALOR", f"R$ {moeda(servico.valor)}", INK, True),
        ("SEU CUSTO", f"R$ {moeda(ag.custo_dirceu)}", INK, True),
        ("RESULTADO", f"R$ {moeda(resultado)}", IN_GREEN if resultado >= 0 else POCKET_RED, True),
        ("HORAS", f"{horas_fmt(ag.horas)}h", INK, True),
        ("STATUS", {"aberto": "Aberto", "finalizado": "Finalizado", "fechado": "Fechado"}.get(servico.status, servico.status), INK, False),
        ("PERÍODO", f"{data_br(servico.data_inicio)} -> {fim}", INK, False),
    ]
    col_w = CONTENT_W / 3
    y0 = pdf.get_y()
    for i, (rotulo, valor, cor, mono) in enumerate(meta):
        cx = MARGIN + (i % 3) * col_w
        cy = y0 + (i // 3) * 13
        pdf.set_xy(cx, cy)
        pdf.set_font("helvetica", "B", 6.5)
        pdf.set_text_color(*SLATE2)
        pdf.cell(col_w, 4, L(rotulo))
        pdf.set_xy(cx, cy + 4)
        pdf.set_font("courier" if mono else "helvetica", "B", 10.5)
        pdf.set_text_color(*cor)
        pdf.cell(col_w, 6, L(valor))
    pdf.set_text_color(*INK)
    pdf.set_y(y0 + 27)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*SLATE)
    if ag.despesas > 0:
        pdf.cell(0, 4.5, L(
            f"Seu custo: diárias do bolso R$ {moeda(ag.bolso_diarias)} + despesas R$ {moeda(ag.despesas)}"
        ), new_x="LMARGIN", new_y="NEXT")
    if ag.custo_epr > 0:
        pdf.cell(0, 4.5, L(
            f"Pago pela EPR (fora do resultado): R$ {moeda(ag.custo_epr)}"
            f" - repasse R$ {moeda(ag.repasse)} . direto R$ {moeda(ag.epr_direto)}"
        ), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    pdf.ln(1)
    _linha_fina(pdf)

    _render_diario(pdf, entradas)

    cor = IN_GREEN if resultado >= 0 else POCKET_RED
    _total_box(pdf, "Resultado do serviço", f"R$ {moeda(resultado)}", cor=cor)
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, L(
        f"Valor R$ {moeda(servico.valor)} - seu custo R$ {moeda(ag.custo_dirceu)} = resultado R$ {moeda(resultado)}"
    ), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    return pdf


# ==================== 2) Consolidado do período ====================

def pdf_periodo(config, de, ate, blocos, totais_gerais, blocos_servicos=None, totais_servicos=None) -> DirceuPDF:
    """blocos: [{maquina, horas, bolso, despesas, custo_dirceu, epr}] — só com atividade.

    Custo do Dirceu (bolso + despesas) e pago pela EPR SEPARADOS — nunca somados.
    """
    label = f"{data_curta(de)} a {data_curta(ate)}"
    pdf = DirceuPDF(config, "Relatório do período", label, rodape_id=f"Período {label}")

    if not blocos:
        _nada(pdf, "Nenhuma máquina com atividade no período.")
    cols = [
        ("Horas", 22, "R"),
        ("Do bolso", 32, "R"),
        ("Despesas", 32, "R"),
        ("Seu custo", 42, "R"),
        ("Pago pela EPR", 54, "R"),
    ]
    for b in blocos:
        m = b["maquina"]
        pdf.quebra_se_preciso(26)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(120, 6, L(m.nome))
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(*SLATE)
        pdf.cell(0, 6, L(f"{m.cliente} . {STATUS_LABEL.get(m.status, m.status)}"),
                 align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*INK)
        _tab_header(pdf, cols)
        y = pdf.get_y()
        pdf.set_font("courier", "", 9)
        x = MARGIN
        valores = [
            f"{horas_fmt(b['horas'])}h",
            moeda(b["bolso"]),
            moeda(b["despesas"]),
            f"R$ {moeda(b['custo_dirceu'])}",
            f"R$ {moeda(b['epr'])}",
        ]
        for (_, w, align), v in zip(cols, valores):
            pdf.set_xy(x, y)
            pdf.cell(w, 6, L(v), align=align)
            x += w
        pdf.set_y(y + 6.4)
        _linha_fina(pdf)
        pdf.ln(2.5)

    _sec(pdf, "Resumo geral do período")
    _tab_header(pdf, cols)
    y = pdf.get_y()
    pdf.set_font("courier", "B", 9)
    x = MARGIN
    valores = [
        f"{horas_fmt(totais_gerais['horas'])}h",
        moeda(totais_gerais["bolso"]),
        moeda(totais_gerais["despesas"]),
        f"R$ {moeda(totais_gerais['custo_dirceu'])}",
        f"R$ {moeda(totais_gerais['epr'])}",
    ]
    for (_, w, align), v in zip(cols, valores):
        pdf.set_xy(x, y)
        pdf.cell(w, 6, L(v), align=align)
        x += w
    pdf.set_y(y + 7)
    _total_box(pdf, "Seu custo do período", f"R$ {moeda(totais_gerais['custo_dirceu'])}")
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, L(f"Pago pela EPR no período (fora da margem): R$ {moeda(totais_gerais['epr'])}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)

    # ---- Serviços avulsos com atividade no período ----
    if blocos_servicos:
        _sec(pdf, "Serviços avulsos no período")
        cols_s = [("Serviço", 78, "L"), ("Horas", 20, "R"), ("Seu custo", 40, "R"), ("Valor", 44, "R")]
        _tab_header(pdf, cols_s)
        for b in blocos_servicos:
            s = b["servico"]
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_font("helvetica", "B", 8.5)
            pdf.set_xy(MARGIN, y)
            pdf.cell(78, 5.5, L(s.descricao[:46]))
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN + 78, y); pdf.cell(20, 5.5, L(f"{horas_fmt(b['horas'])}h"), align="R")
            pdf.set_xy(MARGIN + 98, y); pdf.cell(40, 5.5, L(f"R$ {moeda(b['custo_dirceu'])}"), align="R")
            pdf.set_xy(MARGIN + 138, y); pdf.cell(44, 5.5, L(f"R$ {moeda(s.valor)}"), align="R")
            pdf.set_y(y + 6)
            _linha_fina(pdf)
        if totais_servicos:
            _total_box(pdf, "Valor total dos serviços", f"R$ {moeda(totais_servicos['valor'])}")
    return pdf


# ==================== 3) Saídas — ajudantes ====================

def pdf_ajudantes(config, de, ate, grupos, total_geral) -> DirceuPDF:
    """grupos: [{nome, itens: [{data, maquina, horas, origem, valor}], horas, valor}]."""
    label = f"{data_curta(de)} a {data_curta(ate)}"
    pdf = DirceuPDF(config, "Saídas - ajudantes", label, rodape_id=f"Período {label}")

    cols = [
        ("Data", 24, "L"),
        ("Máquina", 64, "L"),
        ("Horas", 18, "R"),
        ("Origem", 40, "L"),
        ("Valor", 36, "R"),
    ]
    if not grupos:
        _nada(pdf, "Nenhum pagamento a ajudante no período.")
    for g in grupos:
        _sec(pdf, g["nome"])
        _tab_header(pdf, cols)
        for it in g["itens"]:
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN, y)
            pdf.cell(24, 5.5, L(data_br(it["data"])))
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_xy(MARGIN + 24, y)
            pdf.cell(64, 5.5, L(it["maquina"]))
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN + 88, y)
            pdf.cell(18, 5.5, L(f"{horas_fmt(it['horas'])}h"), align="R")
            rotulo, estilo = ORIGEM_CHIP.get(it["origem"], (it["origem"], "pass"))
            _chip(pdf, MARGIN + 110, y + 0.4, rotulo, estilo)
            pdf.set_font("courier", "", 9)
            pdf.set_xy(MARGIN + 146, y)
            pdf.cell(36, 5.5, L(f"R$ {moeda(it['valor'])}"), align="R")
            pdf.set_y(y + 6)
            _linha_fina(pdf)
        # subtotal com destaque (fundo SURF2)
        pdf.quebra_se_preciso(8)
        y = pdf.get_y()
        pdf.set_fill_color(*SURF2)
        pdf.rect(MARGIN, y, CONTENT_W, 7, style="F", round_corners=True, corner_radius=1.5)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_xy(MARGIN + 3, y)
        pdf.cell(80, 7, L(f"Subtotal {g['nome']}"))
        pdf.set_font("courier", "B", 9)
        pdf.set_xy(MARGIN + 88, y)
        pdf.cell(18, 7, L(f"{horas_fmt(g['horas'])}h"), align="R")
        pdf.set_xy(MARGIN + 146, y)
        pdf.cell(36, 7, L(f"R$ {moeda(g['valor'])}"), align="R")
        pdf.set_y(y + 9)

    _total_box(pdf, "Total pago no período", f"R$ {moeda(total_geral)}")
    _nota(pdf, "Origens: Repasse EPR e EPR direto não são custo do Dirceu; 'Do bolso' entra no acerto.")
    return pdf


# ==================== 4) Entradas — recebimentos ====================

def pdf_entradas(config, de, ate, recebimentos, total_receb, repasses, total_repasses) -> DirceuPDF:
    label = f"{data_curta(de)} a {data_curta(ate)}"
    pdf = DirceuPDF(config, "Entradas - recebimentos", label, rodape_id=f"Período {label}")

    cols = [
        ("Data", 24, "L"),
        ("Tipo", 32, "L"),
        ("Máquina", 58, "L"),
        ("Status", 30, "L"),
        ("Valor", 38, "R"),
    ]
    _sec(pdf, "Recebimentos do período")
    if not recebimentos:
        _nada(pdf, "Nenhum recebimento no período.")
    else:
        _tab_header(pdf, cols)
        for r in recebimentos:
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN, y)
            pdf.cell(24, 5.5, L(data_br(r.data)))
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_xy(MARGIN + 24, y)
            pdf.cell(32, 5.5, L("Adiantamento" if r.tipo == "adiantamento" else "Fechamento"))
            pdf.set_xy(MARGIN + 56, y)
            pdf.cell(58, 5.5, L(r.maquina_nome or "-"))
            estilo = "warn" if r.status == "aberto" else "in"
            _chip(pdf, MARGIN + 114, y + 0.4, "Em aberto" if r.status == "aberto" else "Quitado", estilo)
            pdf.set_font("courier", "", 9)
            pdf.set_xy(MARGIN + 144, y)
            pdf.cell(38, 5.5, L(f"R$ {moeda(r.valor)}"), align="R")
            pdf.set_y(y + 6)
            _linha_fina(pdf)
        _total_box(pdf, "Total recebido no período", f"R$ {moeda(total_receb)}")

    _sec(pdf, "Verbas de repasse recebidas")
    if not repasses:
        _nada(pdf, "Nenhuma verba de repasse no período.")
    else:
        cols2 = [("Data", 24, "L"), ("Observação", 120, "L"), ("Valor", 38, "R")]
        _tab_header(pdf, cols2)
        for v in repasses:
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN, y)
            pdf.cell(24, 5.5, L(data_br(v.data)))
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_xy(MARGIN + 24, y)
            pdf.cell(120, 5.5, L(v.obs or "-"))
            pdf.set_font("courier", "", 9)
            pdf.set_xy(MARGIN + 144, y)
            pdf.cell(38, 5.5, L(f"R$ {moeda(v.valor)}"), align="R")
            pdf.set_y(y + 6)
            _linha_fina(pdf)
        y = pdf.get_y()
        pdf.set_font("helvetica", "B", 8)
        pdf.set_xy(MARGIN, y)
        pdf.cell(120, 6, L("Subtotal verbas de repasse"))
        pdf.set_font("courier", "B", 9)
        pdf.set_xy(MARGIN + 144, y)
        pdf.cell(38, 6, L(f"R$ {moeda(total_repasses)}"), align="R")
        pdf.set_y(y + 7)
    _nota(pdf, "Verbas de repasse não são receita do Dirceu: é dinheiro de passagem, "
               "recebido da EPR apenas para pagar ajudantes (prestação de contas).")
    return pdf


# ==================== 5) Fechamento (e prévia) ====================

def pdf_fechamento(config, numero, sub, maquinas, adiantamentos,
                   total_devido, total_adiantado, saldo, obs, previa=False,
                   servicos=None) -> DirceuPDF:
    servicos = servicos or []
    pdf = DirceuPDF(config, "Fechamento", sub, rodape_id=numero)

    if previa:
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*WELD)
        pdf.cell(0, 7, L("PRÉVIA - NÃO REGISTRADO"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*INK)
        pdf.ln(1)

    # ---- Bloco 1: máquinas finalizadas ----
    _sec(pdf, "Máquinas finalizadas (empreita integral)")
    cols = [
        ("Máquina", 56, "L"),
        ("Cliente", 60, "L"),
        ("Finalizada em", 30, "L"),
        ("Empreita", 36, "R"),
    ]
    _tab_header(pdf, cols)
    for m in maquinas:
        pdf.quebra_se_preciso(7)
        y = pdf.get_y()
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_xy(MARGIN, y)
        pdf.cell(56, 5.5, L(m.nome))
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_xy(MARGIN + 56, y)
        pdf.cell(60, 5.5, L(m.cliente))
        pdf.set_font("courier", "", 8.5)
        pdf.set_xy(MARGIN + 116, y)
        pdf.cell(30, 5.5, L(data_br(m.data_finalizacao) if m.data_finalizacao else "-"))
        pdf.set_font("courier", "", 9)
        pdf.set_xy(MARGIN + 146, y)
        pdf.cell(36, 5.5, L(f"R$ {moeda(m.empreita)}"), align="R")
        pdf.set_y(y + 6)
        _linha_fina(pdf)
    if not maquinas:
        _nada(pdf, "Nenhuma máquina finalizada no período.")

    # ---- Bloco 1b: serviços avulsos finalizados ----
    if servicos:
        _sec(pdf, "Serviços avulsos finalizados")
        cols_s = [("Serviço", 66, "L"), ("Cliente", 50, "L"), ("Finalizado em", 30, "L"), ("Valor", 36, "R")]
        _tab_header(pdf, cols_s)
        for s in servicos:
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_font("helvetica", "B", 8.5)
            pdf.set_xy(MARGIN, y)
            pdf.cell(66, 5.5, L(s.descricao[:40]))
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_xy(MARGIN + 66, y)
            pdf.cell(50, 5.5, L(s.cliente or "-"))
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN + 116, y)
            pdf.cell(30, 5.5, L(data_br(s.data_finalizacao) if s.data_finalizacao else "-"))
            pdf.set_font("courier", "", 9)
            pdf.set_xy(MARGIN + 146, y)
            pdf.cell(36, 5.5, L(f"R$ {moeda(s.valor)}"), align="R")
            pdf.set_y(y + 6)
            _linha_fina(pdf)

    # ---- Total devido (máquinas + serviços) ----
    y = pdf.get_y()
    pdf.set_font("helvetica", "B", 8)
    pdf.set_xy(MARGIN, y)
    pdf.cell(120, 6, L("TOTAL DEVIDO"))
    pdf.set_font("courier", "B", 9.5)
    pdf.set_xy(MARGIN + 144, y)
    pdf.cell(38, 6, L(f"R$ {moeda(total_devido)}"), align="R")
    pdf.set_y(y + 7)

    # ---- Bloco 2: adiantamentos abatidos ----
    _sec(pdf, "Adiantamentos abatidos")
    if not adiantamentos:
        _nada(pdf, "Nenhum adiantamento a abater.")
    else:
        cols2 = [("Data", 28, "L"), ("Máquina", 96, "L"), ("Valor", 58, "R")]
        _tab_header(pdf, cols2)
        for a in adiantamentos:
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN, y)
            pdf.cell(28, 5.5, L(data_br(a.data)))
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_xy(MARGIN + 28, y)
            vinculo = a.maquina_nome or a.servico_nome or "- (sem vínculo)"
            pdf.cell(96, 5.5, L(vinculo))
            pdf.set_font("courier", "", 9)
            pdf.set_text_color(*WARN)
            pdf.set_xy(MARGIN + 124, y)
            pdf.cell(58, 5.5, L(f"- R$ {moeda(a.valor)}"), align="R")
            pdf.set_text_color(*INK)
            pdf.set_y(y + 6)
            _linha_fina(pdf)
        y = pdf.get_y()
        pdf.set_font("helvetica", "B", 8)
        pdf.set_xy(MARGIN, y)
        pdf.cell(120, 6, L("TOTAL ADIANTADO"))
        pdf.set_font("courier", "B", 9.5)
        pdf.set_text_color(*WARN)
        pdf.set_xy(MARGIN + 124, y)
        pdf.cell(58, 6, L(f"- R$ {moeda(total_adiantado)}"), align="R")
        pdf.set_text_color(*INK)
        pdf.set_y(y + 7)

    # ---- Régua visual: adiantado (WARN) x saldo (IN_GREEN), proporcional ----
    if total_devido > 0:
        pdf.quebra_se_preciso(22)
        pdf.ln(2)
        y = pdf.get_y()
        h = 8
        frac_ad = min(float(total_adiantado) / float(total_devido), 1.0)
        w_ad = CONTENT_W * frac_ad
        pdf.set_fill_color(*WARN)
        if w_ad > 0.5:
            pdf.rect(MARGIN, y, w_ad, h, style="F", round_corners=True, corner_radius=1.5)
        pdf.set_fill_color(*IN_GREEN)
        if CONTENT_W - w_ad > 0.5:
            pdf.rect(MARGIN + w_ad, y, CONTENT_W - w_ad, h, style="F",
                     round_corners=True, corner_radius=1.5)
        # legenda
        ly = y + h + 2.5
        pdf.set_fill_color(*WARN)
        pdf.rect(MARGIN, ly + 0.7, 3, 3, style="F")
        pdf.set_font("helvetica", "", 7.5)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(MARGIN + 4.5, ly)
        pdf.cell(80, 4.5, L(f"Adiantado: R$ {moeda(total_adiantado)}"))
        pdf.set_fill_color(*IN_GREEN)
        pdf.rect(MARGIN + 92, ly + 0.7, 3, 3, style="F")
        pdf.set_xy(MARGIN + 96.5, ly)
        pdf.cell(80, 4.5, L(f"Saldo: R$ {moeda(saldo)}"))
        pdf.set_text_color(*INK)
        pdf.set_y(ly + 7)

    # ---- Caixa do saldo ----
    if saldo > 0:
        _total_box(pdf, "Saldo a receber", f"R$ {moeda(saldo)}")
    else:
        _total_box(pdf, "Saldo", f"R$ {moeda(saldo)}")
        _nota(pdf, "O total adiantado cobriu (ou superou) o valor devido - "
                   "nenhum valor novo a receber neste acerto.")

    if obs:
        _sec(pdf, "Observações")
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_text_color(*SLATE)
        pdf.multi_cell(CONTENT_W, 4.5, L(obs))
        pdf.set_text_color(*INK)
    return pdf


# ==================== 6) Resultado do período (ganho real) ====================

def pdf_resultado(config, de, ate, recebimentos, total_entradas,
                  bolso_rows, total_bolso, despesas, total_despesas,
                  total_saidas, resultado) -> DirceuPDF:
    """Confronto entradas × saídas do bolso. bolso_rows: (data, ajudante, maquina, valor)."""
    label = f"{data_curta(de)} a {data_curta(ate)}"
    pdf = DirceuPDF(config, "Resultado do período", label, rodape_id=f"Período {label}")

    # ---- Bloco 1: entradas ----
    _sec(pdf, "Entradas — recebido no período")
    if not recebimentos:
        _nada(pdf, "Nenhum recebimento no período.")
    else:
        cols = [("Data", 24, "L"), ("Tipo", 32, "L"), ("Máquina", 88, "L"), ("Valor", 38, "R")]
        _tab_header(pdf, cols)
        for r in recebimentos:
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN, y)
            pdf.cell(24, 5.5, L(data_br(r.data)))
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_xy(MARGIN + 24, y)
            pdf.cell(32, 5.5, L("Adiantamento" if r.tipo == "adiantamento" else "Fechamento"))
            pdf.set_xy(MARGIN + 56, y)
            pdf.cell(88, 5.5, L(r.maquina_nome or "-"))
            pdf.set_font("courier", "", 9)
            pdf.set_text_color(*IN_GREEN)
            pdf.set_xy(MARGIN + 144, y)
            pdf.cell(38, 5.5, L(f"R$ {moeda(r.valor)}"), align="R")
            pdf.set_text_color(*INK)
            pdf.set_y(y + 6)
            _linha_fina(pdf)
    y = pdf.get_y()
    pdf.set_font("helvetica", "B", 8)
    pdf.set_xy(MARGIN, y)
    pdf.cell(120, 6, L("TOTAL DE ENTRADAS"))
    pdf.set_font("courier", "B", 9.5)
    pdf.set_text_color(*IN_GREEN)
    pdf.set_xy(MARGIN + 144, y)
    pdf.cell(38, 6, L(f"R$ {moeda(total_entradas)}"), align="R")
    pdf.set_text_color(*INK)
    pdf.set_y(y + 7)

    # ---- Bloco 2: saídas do bolso ----
    _sec(pdf, "Saídas do bolso")
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, L("Diárias pagas do bolso"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    if not bolso_rows:
        _nada(pdf, "Nenhuma diária do bolso no período.")
    else:
        cols = [("Data", 24, "L"), ("Ajudante", 56, "L"), ("Máquina", 64, "L"), ("Valor", 38, "R")]
        _tab_header(pdf, cols)
        for data_e, ajudante, maquina, valor in bolso_rows:
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN, y)
            pdf.cell(24, 5.5, L(data_br(data_e)))
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_xy(MARGIN + 24, y)
            pdf.cell(56, 5.5, L(ajudante))
            pdf.set_xy(MARGIN + 80, y)
            pdf.cell(64, 5.5, L(maquina))
            pdf.set_font("courier", "", 9)
            pdf.set_text_color(*POCKET_RED)
            pdf.set_xy(MARGIN + 144, y)
            pdf.cell(38, 5.5, L(f"- R$ {moeda(valor)}"), align="R")
            pdf.set_text_color(*INK)
            pdf.set_y(y + 6)
            _linha_fina(pdf)
        y = pdf.get_y()
        pdf.set_font("helvetica", "B", 8)
        pdf.set_xy(MARGIN, y)
        pdf.cell(120, 6, L("Subtotal diárias do bolso"))
        pdf.set_font("courier", "B", 9)
        pdf.set_text_color(*POCKET_RED)
        pdf.set_xy(MARGIN + 144, y)
        pdf.cell(38, 6, L(f"- R$ {moeda(total_bolso)}"), align="R")
        pdf.set_text_color(*INK)
        pdf.set_y(y + 7)

    pdf.ln(1)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, L("Despesas"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    if not despesas:
        _nada(pdf, "Nenhuma despesa no período.")
    else:
        cols = [("Data", 24, "L"), ("Categoria", 34, "L"), ("Descrição", 86, "L"), ("Valor", 38, "R")]
        _tab_header(pdf, cols)
        for d in despesas:
            pdf.quebra_se_preciso(7)
            y = pdf.get_y()
            pdf.set_font("courier", "", 8.5)
            pdf.set_xy(MARGIN, y)
            pdf.cell(24, 5.5, L(data_br(d.data)))
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_xy(MARGIN + 24, y)
            pdf.cell(34, 5.5, L(CATEGORIA_LABEL.get(d.categoria, d.categoria)))
            pdf.set_xy(MARGIN + 58, y)
            desc = d.descricao or "-"
            if d.maquina_nome:
                desc = f"{desc} ({d.maquina_nome})" if d.descricao else d.maquina_nome
            pdf.cell(86, 5.5, L(desc[:52]))
            pdf.set_font("courier", "", 9)
            pdf.set_text_color(*POCKET_RED)
            pdf.set_xy(MARGIN + 144, y)
            pdf.cell(38, 5.5, L(f"- R$ {moeda(d.valor)}"), align="R")
            pdf.set_text_color(*INK)
            pdf.set_y(y + 6)
            _linha_fina(pdf)
        y = pdf.get_y()
        pdf.set_font("helvetica", "B", 8)
        pdf.set_xy(MARGIN, y)
        pdf.cell(120, 6, L("Subtotal despesas"))
        pdf.set_font("courier", "B", 9)
        pdf.set_text_color(*POCKET_RED)
        pdf.set_xy(MARGIN + 144, y)
        pdf.cell(38, 6, L(f"- R$ {moeda(total_despesas)}"), align="R")
        pdf.set_text_color(*INK)
        pdf.set_y(y + 7)

    y = pdf.get_y()
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_xy(MARGIN, y)
    pdf.cell(120, 6, L("TOTAL DE SAÍDAS"))
    pdf.set_font("courier", "B", 9.5)
    pdf.set_text_color(*POCKET_RED)
    pdf.set_xy(MARGIN + 144, y)
    pdf.cell(38, 6, L(f"- R$ {moeda(total_saidas)}"), align="R")
    pdf.set_text_color(*INK)
    pdf.set_y(y + 8)

    # ---- Barra entradas × saídas (proporcional) ----
    soma = float(total_entradas) + float(total_saidas)
    if soma > 0:
        pdf.quebra_se_preciso(16)
        y = pdf.get_y()
        h = 7
        w_ent = CONTENT_W * float(total_entradas) / soma
        pdf.set_fill_color(*IN_GREEN)
        if w_ent > 0.5:
            pdf.rect(MARGIN, y, w_ent, h, style="F", round_corners=True, corner_radius=1.5)
        pdf.set_fill_color(*POCKET_RED)
        if CONTENT_W - w_ent > 0.5:
            pdf.rect(MARGIN + w_ent, y, CONTENT_W - w_ent, h, style="F",
                     round_corners=True, corner_radius=1.5)
        ly = y + h + 2
        pdf.set_font("helvetica", "", 7.5)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(MARGIN, ly)
        pdf.cell(90, 4.5, L(f"Entradas: R$ {moeda(total_entradas)}"))
        pdf.set_xy(PAGE_W - MARGIN - 90, ly)
        pdf.cell(90, 4.5, L(f"Saídas: R$ {moeda(total_saidas)}"), align="R")
        pdf.set_text_color(*INK)
        pdf.set_y(ly + 7)

    # ---- Resultado (verde/vermelho) ----
    cor = IN_GREEN if resultado >= 0 else POCKET_RED
    _total_box(pdf, "Resultado do período", f"R$ {moeda(resultado)}", cor=cor)
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, L(f"Entradas R$ {moeda(total_entradas)} - Saídas R$ {moeda(total_saidas)}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    _nota(pdf, "Repasses da EPR e pagamentos diretos da EPR não entram: "
               "não são receita nem custo do Dirceu.")
    return pdf


# ==================== 7) Consolidado de máquinas por status ====================

def pdf_maquinas_consolidado(config, rotulo_status, blocos, totais) -> DirceuPDF:
    """blocos: [{maquina, ag, margem, pct, entradas(<=10 recentes), mais_n}]."""
    pdf = DirceuPDF(config, f"Máquinas - {rotulo_status}",
                    f"{len(blocos)} máquina(s)", rodape_id=f"Máquinas {rotulo_status}")

    for b in blocos:
        m, ag = b["maquina"], b["ag"]
        pdf.quebra_se_preciso(30)
        pdf.ln(1)
        pdf._losango(MARGIN + 1.5, pdf.get_y() + 3, 1.5)
        pdf.set_xy(MARGIN + 6, pdf.get_y())
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(95, 6, L(m.nome))
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(*SLATE)
        pdf.cell(0, 6, L(f"{m.cliente} . {STATUS_LABEL.get(m.status, m.status)}"),
                 align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*INK)
        pdf.set_font("courier", "B", 9)
        pdf.set_x(MARGIN + 6)
        pdf.cell(0, 5.5, L(
            f"empreita R$ {moeda(m.empreita)}  .  seu custo R$ {moeda(ag.custo_dirceu)}"
            f"  .  margem R$ {moeda(b['margem'])}  .  {horas_fmt(ag.horas)}h"
        ), new_x="LMARGIN", new_y="NEXT")
        if ag.custo_epr > 0:
            pdf.set_font("helvetica", "", 7.5)
            pdf.set_text_color(*SLATE)
            pdf.set_x(MARGIN + 6)
            pdf.cell(0, 4.5, L(f"EPR pagou R$ {moeda(ag.custo_epr)} (fora da margem)"),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*INK)
        for e in b["entradas"]:
            pdf.quebra_se_preciso(6)
            y = pdf.get_y()
            pdf.set_font("courier", "", 8)
            pdf.set_xy(MARGIN + 6, y)
            pdf.cell(22, 4.8, L(data_br(e.data)))
            pdf.set_font("helvetica", "", 8)
            pdf.set_xy(MARGIN + 28, y)
            desc = e.descricao if len(e.descricao) <= 78 else e.descricao[:78] + "..."
            pdf.cell(126, 4.8, L(desc))
            pdf.set_font("courier", "", 8)
            pdf.set_xy(PAGE_W - MARGIN - 22, y)
            horas_dia = sum((Decimal(str(t.horas)) for t in e.trabalhos), Decimal("0"))
            pdf.cell(22, 4.8, L(f"{horas_fmt(horas_dia)}h"), align="R")
            pdf.set_y(y + 5)
        if b["mais_n"] > 0:
            pdf.set_font("helvetica", "I", 7.5)
            pdf.set_text_color(*SLATE2)
            pdf.set_x(MARGIN + 6)
            pdf.cell(0, 4.5, L(f"... e mais {b['mais_n']} lançamento(s)"),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*INK)
        if not b["entradas"]:
            pdf.set_font("helvetica", "I", 7.5)
            pdf.set_text_color(*SLATE2)
            pdf.set_x(MARGIN + 6)
            pdf.cell(0, 4.5, L("Sem lançamentos no diário."), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*INK)
        pdf.ln(1.5)
        _linha_fina(pdf)

    # ---- resumo final ----
    _sec(pdf, "Resumo")
    cols = [("Máquina", 46, "L"), ("Empreita", 28, "R"), ("Seu custo", 28, "R"),
            ("EPR pagou", 28, "R"), ("Margem", 28, "R"), ("Horas", 24, "R")]
    _tab_header(pdf, cols)
    for b in blocos:
        pdf.quebra_se_preciso(7)
        y = pdf.get_y()
        m, ag = b["maquina"], b["ag"]
        pdf.set_font("helvetica", "B", 8)
        pdf.set_xy(MARGIN, y)
        pdf.cell(46, 5.5, L(m.nome[:28]))
        pdf.set_font("courier", "", 8.5)
        for i, v in enumerate([moeda(m.empreita), moeda(ag.custo_dirceu),
                               moeda(ag.custo_epr), moeda(b["margem"]),
                               f"{horas_fmt(ag.horas)}h"]):
            pdf.set_xy(MARGIN + 46 + 28 * i - (4 if i == 4 else 0), y)
            pdf.cell(28 if i < 4 else 24, 5.5, L(v), align="R")
        pdf.set_y(y + 6)
        _linha_fina(pdf)
    _total_box(pdf, "Seu custo total", f"R$ {moeda(totais['custo_dirceu'])}")
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, L(
        f"Empreitas R$ {moeda(totais['empreita'])} . margem total R$ {moeda(totais['margem'])}"
        f" . EPR pagou R$ {moeda(totais['epr'])} . {horas_fmt(totais['horas'])}h"
    ), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    return pdf


# ==================== 8) Consolidado de serviços avulsos por período ====================

def pdf_servicos_periodo(config, de, ate, finalizados, andamento, totais) -> DirceuPDF:
    """Só serviços avulsos (NÃO inclui máquinas).

    finalizados/andamento: [{servico, ag, resultado, pct, entradas(<=10), mais_n}].
    O RESULTADO consolidado soma apenas os FINALIZADOS no período (ganho real).
    """
    label = f"{data_curta(de)} a {data_curta(ate)}"
    pdf = DirceuPDF(config, "Serviços avulsos - período", label, rodape_id=f"Serviços {label}")

    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*SLATE)
    pdf.multi_cell(CONTENT_W, 4.5, L(
        "Só serviços avulsos (não inclui máquinas). O resultado consolidado soma os "
        "serviços FINALIZADOS no período (por data de finalização)."
    ))
    pdf.set_text_color(*INK)
    pdf.ln(1)

    def _bloco(b, incluir_diario=True):
        s, ag = b["servico"], b["ag"]
        pdf.quebra_se_preciso(24)
        pdf.ln(1)
        pdf._losango(MARGIN + 1.5, pdf.get_y() + 3, 1.5)
        pdf.set_xy(MARGIN + 6, pdf.get_y())
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(110, 6, L(s.descricao[:52]))
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(*SLATE)
        pdf.cell(0, 6, L((s.cliente or "-") + " . " + {"aberto": "Aberto", "finalizado": "Finalizado", "fechado": "Fechado"}.get(s.status, s.status)),
                 align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*INK)
        pdf.set_font("courier", "B", 9)
        pdf.set_x(MARGIN + 6)
        cor = IN_GREEN if b["resultado"] >= 0 else POCKET_RED
        pdf.write(5.5, L(
            f"valor R$ {moeda(s.valor)}  .  seu custo R$ {moeda(ag.custo_dirceu)}"
            f"  .  {horas_fmt(ag.horas)}h  .  resultado "
        ))
        pdf.set_text_color(*cor)
        pdf.write(5.5, L(f"R$ {moeda(b['resultado'])}"))
        pdf.set_text_color(*INK)
        pdf.ln(6)
        if ag.custo_epr > 0:
            pdf.set_font("helvetica", "", 7.5)
            pdf.set_text_color(*SLATE)
            pdf.set_x(MARGIN + 6)
            pdf.cell(0, 4.5, L(f"EPR pagou R$ {moeda(ag.custo_epr)} (fora do resultado)"),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*INK)
        if incluir_diario:
            for e in b["entradas"]:
                pdf.quebra_se_preciso(6)
                y = pdf.get_y()
                pdf.set_font("courier", "", 8)
                pdf.set_xy(MARGIN + 6, y)
                pdf.cell(22, 4.8, L(data_br(e.data)))
                pdf.set_font("helvetica", "", 8)
                pdf.set_xy(MARGIN + 28, y)
                desc = e.descricao if len(e.descricao) <= 78 else e.descricao[:78] + "..."
                pdf.cell(126, 4.8, L(desc))
                pdf.set_font("courier", "", 8)
                horas_dia = sum((Decimal(str(t.horas)) for t in e.trabalhos), Decimal("0"))
                pdf.set_xy(PAGE_W - MARGIN - 22, y)
                pdf.cell(22, 4.8, L(f"{horas_fmt(horas_dia)}h"), align="R")
                pdf.set_y(y + 5)
            if b["mais_n"] > 0:
                pdf.set_font("helvetica", "I", 7.5)
                pdf.set_text_color(*SLATE2)
                pdf.set_x(MARGIN + 6)
                pdf.cell(0, 4.5, L(f"... e mais {b['mais_n']} lançamento(s)"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(*INK)
        pdf.ln(1.5)
        _linha_fina(pdf)

    _sec(pdf, "Serviços finalizados no período")
    if not finalizados:
        _nada(pdf, "Nenhum serviço avulso finalizado no período.")
    for b in finalizados:
        _bloco(b)

    if andamento:
        _sec(pdf, "Em andamento com atividade no período (informativo)")
        for b in andamento:
            _bloco(b, incluir_diario=False)

    # ---- resumo dos FINALIZADOS ----
    _sec(pdf, "Resumo dos finalizados")
    cols = [("Serviço", 74, "L"), ("Valor", 34, "R"), ("Seu custo", 36, "R"), ("Resultado", 38, "R")]
    _tab_header(pdf, cols)
    for b in finalizados:
        pdf.quebra_se_preciso(7)
        y = pdf.get_y()
        s, ag = b["servico"], b["ag"]
        pdf.set_font("helvetica", "B", 8)
        pdf.set_xy(MARGIN, y)
        pdf.cell(74, 5.5, L(s.descricao[:44]))
        pdf.set_font("courier", "", 8.5)
        pdf.set_xy(MARGIN + 74, y); pdf.cell(34, 5.5, L(f"R$ {moeda(s.valor)}"), align="R")
        pdf.set_xy(MARGIN + 108, y); pdf.cell(36, 5.5, L(f"R$ {moeda(ag.custo_dirceu)}"), align="R")
        pdf.set_text_color(*(IN_GREEN if b["resultado"] >= 0 else POCKET_RED))
        pdf.set_xy(MARGIN + 144, y); pdf.cell(38, 5.5, L(f"R$ {moeda(b['resultado'])}"), align="R")
        pdf.set_text_color(*INK)
        pdf.set_y(y + 6)
        _linha_fina(pdf)

    cor = IN_GREEN if totais["resultado"] >= 0 else POCKET_RED
    _total_box(pdf, "Resultado dos serviços no período", f"R$ {moeda(totais['resultado'])}", cor=cor)
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, L(
        f"Recebido R$ {moeda(totais['valor'])} - seu custo R$ {moeda(totais['custo_dirceu'])}"
        f" = resultado R$ {moeda(totais['resultado'])} . {horas_fmt(totais['horas'])}h"
    ), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    return pdf
