import { MaquinaStatus, Origem, ServicoStatus } from './models';

/** Textos/classes do protótipo (ST e ORG). */
export const STATUS_BADGE: Record<MaquinaStatus, [string, string]> = {
  andamento: ['Em andamento', 'b-and'],
  finalizada: ['Finalizada · aguardando fechamento', 'b-fin'],
  fechada: ['Fechada e recebida', 'b-fech'],
};

export const STATUS_SERVICO: Record<ServicoStatus, [string, string]> = {
  aberto: ['Aberto', 'b-and'],
  finalizado: ['Finalizado · aguardando fechamento', 'b-fin'],
  fechado: ['Fechado e recebido', 'b-fech'],
};

export const ORIGEM_CHIP: Record<Origem | 'proprio', [string, string]> = {
  repasse: ['Repasse EPR', 'c-rep'],
  epr_direto: ['EPR direto', 'c-epr'],
  bolso: ['Do bolso', 'c-bolso'],
  proprio: ['Empreita', 'c-neutral'], // "Eu trabalhei" — sem valor
};

export const CATEGORIA_DESPESA: Record<string, string> = {
  deslocamento: 'Deslocamento',
  alimentacao: 'Alimentação',
  material: 'Material',
  outros: 'Outros',
};

/** Classe da barra de consumo (protótipo: >70 hot, >45 padrão, senão ok). */
export function barClass(pct: number): string {
  return pct > 70 ? 'hot' : pct > 45 ? '' : 'ok';
}
