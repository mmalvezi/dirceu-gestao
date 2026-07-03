"""Utilitários de formatação pt-BR (dashboard, resumo WhatsApp e PDFs da Fase 10)."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def moeda(valor) -> str:
    """Formata número no padrão pt-BR: 1234.56 -> '1.234,56'; 1120 -> '1.120'.

    Centavos só aparecem quando existem (como no protótipo: 'R$ 1.120').
    """
    d = Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    negativo = d < 0
    d = abs(d)
    inteiro = int(d)
    centavos = int((d - inteiro) * 100)
    s = f"{inteiro:,}".replace(",", ".")
    if centavos:
        s += f",{centavos:02d}"
    return ("-" if negativo else "") + s


def horas_fmt(valor) -> str:
    """Formata horas: 46.0 -> '46'; 7.5 -> '7,5'."""
    d = Decimal(str(valor or 0)).normalize()
    if d == d.to_integral_value():
        return str(int(d))
    return str(d).replace(".", ",")


def data_curta(d: date) -> str:
    """dd/mm (para labels tipo '29/06 a 05/07')."""
    return d.strftime("%d/%m")


def data_br(d: date) -> str:
    """dd/mm/aaaa."""
    return d.strftime("%d/%m/%Y")
