import { MaquinaStatus, Origem } from './models';

/** Textos/classes do protótipo (ST e ORG). */
export const STATUS_BADGE: Record<MaquinaStatus, [string, string]> = {
  andamento: ['Em andamento', 'b-and'],
  finalizada: ['Finalizada · aguardando fechamento', 'b-fin'],
  fechada: ['Fechada e recebida', 'b-fech'],
};

export const ORIGEM_CHIP: Record<Origem, [string, string]> = {
  repasse: ['Repasse EPR', 'c-rep'],
  epr_direto: ['EPR direto', 'c-epr'],
  bolso: ['Do bolso', 'c-bolso'],
};

/** Classe da barra de consumo (protótipo: >70 hot, >45 padrão, senão ok). */
export function barClass(pct: number): string {
  return pct > 70 ? 'hot' : pct > 45 ? '' : 'ok';
}
