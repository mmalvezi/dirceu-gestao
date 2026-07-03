/** Interfaces espelhando os JSONs da API (backend FastAPI na 8002). */

export type Origem = 'repasse' | 'epr_direto' | 'bolso';
export type MaquinaStatus = 'andamento' | 'finalizada' | 'fechada';
export type RecebimentoTipo = 'adiantamento' | 'fechamento';
export type RecebimentoStatus = 'aberto' | 'quitado';

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Usuario {
  id: number;
  username: string;
}

export interface Config {
  nome_exibicao: string;
  telefone: string | null;
  logo_filename: string | null;
  logo_url: string | null;
}

export interface Ajudante {
  id: number;
  nome: string;
  telefone: string | null;
  valor_hora_padrao: number | null;
  obs: string | null;
  ativo: boolean;
}

export interface UltimoLancamento {
  data: string; // YYYY-MM-DD
  descricao: string;
}

export interface Maquina {
  id: number;
  nome: string;
  cliente: string;
  empreita: number;
  status: MaquinaStatus;
  data_inicio: string;
  data_finalizacao: string | null;
  obs: string | null;
  custo: number;
  horas: number;
  margem: number;
  pct_consumido: number;
  ultimo_lancamento: UltimoLancamento | null;
}

export interface Trabalho {
  id: number;
  ajudante_id: number | null;
  ajudante_nome: string;
  horas: number;
  valor: number;
  origem: Origem;
}

export interface DiarioEntrada {
  id: number;
  maquina_id: number;
  data: string;
  descricao: string;
  trabalhos: Trabalho[];
  total_horas: number;
  total_valor: number;
  aviso?: string | null; // só na resposta de POST/PUT
}

export interface MaquinaDetalhe extends Maquina {
  diario: DiarioEntrada[];
}

export interface Recebimento {
  id: number;
  tipo: RecebimentoTipo;
  data: string;
  valor: number;
  maquina_id: number | null;
  maquina_nome: string | null;
  status: RecebimentoStatus;
  fechamento_id: number | null;
  obs: string | null;
}

export interface RepasseEntrada {
  id: number;
  data: string;
  valor: number;
  obs: string | null;
}

export interface Pagamento {
  data: string;
  ajudante_id: number | null;
  ajudante_nome: string;
  maquina_id: number;
  maquina_nome: string;
  horas: number;
  valor: number;
  origem: Origem;
}

export interface FinanceiroTotais {
  periodo_de: string;
  periodo_ate: string;
  repasse_recebido: number;
  repasse_pago: number;
  caixa_repasse: number;
  saido_bolso: number;
  pago_epr_direto: number;
  custo_total_ajudantes: number;
  adiantado_aberto: number;
}

// ----- Fechamento -----

export interface FechamentoMaquina {
  id: number;
  nome: string;
  cliente: string;
  empreita: number;
  data_finalizacao: string | null;
}

export interface FechamentoAdiantamento {
  id: number;
  data: string;
  valor: number;
  maquina_id: number | null;
  maquina_nome: string | null;
}

export interface FechamentoPrevia {
  periodo_de: string;
  periodo_ate: string;
  maquinas: FechamentoMaquina[];
  adiantamentos: FechamentoAdiantamento[];
  total_devido: number;
  total_adiantado: number;
  saldo: number;
  pode_registrar: boolean;
}

export interface Fechamento {
  id: number;
  numero: string;
  data_geracao: string;
  periodo_de: string;
  periodo_ate: string;
  total_devido: number;
  total_adiantado: number;
  saldo: number;
  obs: string | null;
  maquinas: FechamentoMaquina[];
}

export interface FechamentoDetalhe extends Fechamento {
  adiantamentos: FechamentoAdiantamento[];
  recebimento_fechamento: Recebimento | null;
}

// ----- Dashboard -----

export interface DashboardPeriodo {
  de: string;
  ate: string;
  label: string;
}

export interface PagoAjudantes {
  total: number;
  repasse: number;
  bolso: number;
  epr_direto: number;
}

export interface AdiantadoAberto {
  total: number;
  quantidade: number;
}

export interface AReceberMaquina {
  nome: string;
  valor: number;
}

export interface AReceber {
  total: number;
  maquinas: AReceberMaquina[];
}

export interface DashboardKpis {
  horas_periodo: number;
  ajudantes_ativos_periodo: number;
  pago_ajudantes: PagoAjudantes;
  adiantado_aberto: AdiantadoAberto;
  a_receber: AReceber;
}

export interface HorasDia {
  dia: string;
  data: string;
  horas: number;
  hoje: boolean;
}

export interface MaquinaAndamento {
  id: number;
  nome: string;
  status: MaquinaStatus;
  empreita: number;
  custo: number;
  margem: number;
  pct_consumido: number;
}

export interface Aviso {
  nivel: 'warn' | 'hot' | 'info';
  texto: string;
}

export interface Dashboard {
  periodo: DashboardPeriodo;
  kpis: DashboardKpis;
  horas_por_dia: HorasDia[];
  maquinas_andamento: MaquinaAndamento[];
  avisos: Aviso[];
  resumo_whatsapp: string;
}
