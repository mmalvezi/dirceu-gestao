/** Formatação pt-BR — espelha o utils.py do backend.
 *
 * IMPORTANTE: datas chegam como string 'YYYY-MM-DD' e são formatadas por SPLIT,
 * nunca com new Date('YYYY-MM-DD') — que interpreta como UTC e volta um dia
 * em fusos negativos (regra de ouro nº 6 do plano).
 */

/** R$ 1.234,56 — centavos só quando existem (igual ao moeda() do backend). */
export function formatMoney(v: number | null | undefined): string {
  const total = Math.round((v ?? 0) * 100);
  const negativo = total < 0;
  const abs = Math.abs(total);
  const inteiro = Math.floor(abs / 100);
  const centavos = abs % 100;
  let s = inteiro.toLocaleString('pt-BR');
  if (centavos) s += ',' + String(centavos).padStart(2, '0');
  return (negativo ? '-' : '') + 'R$ ' + s;
}

/** 46 -> '46'; 7.5 -> '7,5'. */
export function formatHours(v: number | null | undefined): string {
  const n = v ?? 0;
  if (Number.isInteger(n)) return String(n);
  return String(n).replace('.', ',');
}

/** 'YYYY-MM-DD' -> 'dd/mm/aaaa' (por split, sem Date). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const [a, m, d] = iso.split('-');
  return `${d}/${m}/${a}`;
}

/** 'YYYY-MM-DD' -> 'dd/mm'. */
export function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return '';
  const [, m, d] = iso.split('-');
  return `${d}/${m}`;
}

/** 'YYYY-MM-DD' -> 'qua, 01/07' (dia da semana via Date LOCAL — sem parse de string). */
export function formatDateDia(iso: string | null | undefined): string {
  if (!iso) return '';
  const [a, m, d] = iso.split('-').map(Number);
  const dias = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];
  const wd = dias[new Date(a, m - 1, d).getDay()];
  return `${wd}, ${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}`;
}

/** Data de hoje como 'YYYY-MM-DD' (para inputs type=date). */
export function todayIso(): string {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

/** Primeiro dia do mês corrente como 'YYYY-MM-DD'. */
export function primeiroDiaMesIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
}

/** Primeiro dia do mês ANTERIOR como 'YYYY-MM-DD'. */
export function primeiroDiaMesAnteriorIso(): string {
  const d = new Date();
  const m = new Date(d.getFullYear(), d.getMonth() - 1, 1);
  return `${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, '0')}-01`;
}
