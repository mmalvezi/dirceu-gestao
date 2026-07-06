import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/api.service';
import { Icon } from '../../core/icon';
import { STATUS_BADGE, STATUS_SERVICO } from '../../core/labels';
import { Ajudante, Fechamento, Maquina, Servico } from '../../core/models';
import { AjudanteService } from '../../core/services/ajudante.service';
import { FechamentoService } from '../../core/services/fechamento.service';
import { MaquinaService } from '../../core/services/maquina.service';
import { ServicoService } from '../../core/services/servico.service';
import { formatDate, primeiroDiaMesIso, todayIso } from '../../core/format';
import { Modal } from '../../shared/modal';

type TipoRel =
  | 'maquina'
  | 'servico'
  | 'periodo'
  | 'ajudantes'
  | 'entradas'
  | 'fechamento'
  | 'resultado';

interface CardRel {
  tipo: TipoRel;
  titulo: string;
  desc: string;
}

/** Relatórios em PDF (scrRelatorios): 5 cards + mini-modal de parâmetros. */
@Component({
  selector: 'app-relatorios',
  imports: [FormsModule, Modal, Icon],
  templateUrl: './relatorios.html',
})
export class RelatoriosPage implements OnInit {
  private api = inject(ApiService);
  private maquinasSvc = inject(MaquinaService);
  private servicosSvc = inject(ServicoService);
  private ajudantesSvc = inject(AjudanteService);
  private fechamentosSvc = inject(FechamentoService);

  fmtData = formatDate;
  badge = STATUS_BADGE;
  badgeSvc = STATUS_SERVICO;
  FILTROS_STATUS: [string, string][] = [
    ['', 'Todas'], ['andamento', 'Em andamento'], ['finalizada', 'Finalizadas'], ['fechada', 'Fechadas'],
  ];
  FILTROS_STATUS_SVC: [string, string][] = [
    ['', 'Todos'], ['aberto', 'Abertos'], ['finalizado', 'Finalizados'], ['fechado', 'Fechados'],
  ];
  CONSOLIDADOS: [string, string][] = [
    ['todas', 'Todas'], ['andamento', 'Em andamento'], ['finalizada', 'Finalizadas'], ['fechada', 'Fechadas'],
  ];
  selStatus = '';
  selBusca = '';
  selStatusSvc = '';
  selBuscaSvc = '';
  rServicoModo: 'individual' | 'periodo' = 'individual';

  CARDS: CardRel[] = [
    { tipo: 'maquina', titulo: 'Relatório por máquina', desc: 'Diário completo, custos, horas e margem de uma máquina.' },
    { tipo: 'servico', titulo: 'Relatório por serviço', desc: 'Diário, custo, resultado e horas de um serviço avulso.' },
    { tipo: 'periodo', titulo: 'Relatório do período (todas)', desc: 'Tudo que rodou no período, consolidado máquina a máquina.' },
    { tipo: 'ajudantes', titulo: 'Saídas — ajudantes', desc: 'Quanto cada ajudante recebeu, com a origem de cada pagamento.' },
    { tipo: 'entradas', titulo: 'Entradas — recebimentos', desc: 'Adiantamentos e fechamentos recebidos da EPR.' },
    { tipo: 'fechamento', titulo: 'Fechamento', desc: 'O confronto: finalizado no período × adiantado. Pronto pra apresentar.' },
    { tipo: 'resultado', titulo: 'Resultado do período', desc: 'Quanto realmente entrou × o que saiu do bolso. Seu ganho real.' },
  ];

  maquinas = signal<Maquina[]>([]);
  servicos = signal<Servico[]>([]);
  ajudantes = signal<Ajudante[]>([]);
  fechamentos = signal<Fechamento[]>([]);

  modal = signal<TipoRel | null>(null);
  erro = signal('');
  gerando = signal(false);

  // parâmetros
  rMaquinaId = '';
  rServicoId = '';
  rDe = primeiroDiaMesIso();
  rAte = todayIso();
  rAjudanteId = '';
  rFechamentoId = '';
  rModoFech: 'registrado' | 'previa' = 'registrado';

  ngOnInit(): void {
    this.maquinasSvc.listar().subscribe((ms) => this.maquinas.set(ms));
    this.servicosSvc.listar().subscribe((ss) => this.servicos.set(ss));
    this.ajudantesSvc.listar(true).subscribe((as) => this.ajudantes.set(as));
    this.fechamentosSvc.listar().subscribe((fs) => {
      this.fechamentos.set(fs);
      if (fs.length) this.rFechamentoId = String(fs[0].id);
    });
  }

  abrir(tipo: TipoRel): void {
    this.erro.set('');
    if (tipo === 'maquina') {
      this.selStatus = '';
      this.selBusca = '';
      this.rMaquinaId = '';
    }
    if (tipo === 'servico') {
      this.selStatusSvc = '';
      this.selBuscaSvc = '';
      this.rServicoId = '';
      this.rServicoModo = 'individual';
    }
    this.modal.set(tipo);
  }

  servicosFiltrados(): Servico[] {
    const q = this.selBuscaSvc.trim().toLowerCase();
    return this.servicos().filter(
      (s) =>
        (!this.selStatusSvc || s.status === this.selStatusSvc) &&
        (!q || s.descricao.toLowerCase().includes(q) || (s.cliente ?? '').toLowerCase().includes(q)),
    );
  }

  selecionar(m: Maquina): void {
    this.rMaquinaId = String(m.id);
  }

  selecionada(m: Maquina): boolean {
    return this.rMaquinaId === String(m.id);
  }

  maquinasFiltradas(): Maquina[] {
    const q = this.selBusca.trim().toLowerCase();
    return this.maquinas().filter(
      (m) =>
        (!this.selStatus || m.status === this.selStatus) &&
        (!q || m.nome.toLowerCase().includes(q) || m.cliente.toLowerCase().includes(q)),
    );
  }

  contagem(): string {
    const ms = this.maquinasFiltradas();
    const and = ms.filter((m) => m.status === 'andamento').length;
    return `${ms.length} máquina(s)` + (and ? ` · ${and} em andamento` : '');
  }

  gerarConsolidado(status: string): void {
    if (this.gerando()) return;
    this.erro.set('');
    this.gerando.set(true);
    this.api.getBlob('/pdf/maquinas', { status }).subscribe({
      next: (blob) => {
        this.gerando.set(false);
        this.modal.set(null);
        window.open(URL.createObjectURL(blob), '_blank');
      },
      error: (e) => {
        this.gerando.set(false);
        this.erro.set(e?.status === 404 ? 'Nenhuma máquina neste status.' : 'Não foi possível gerar o PDF.');
      },
    });
  }

  gerar(): void {
    const t = this.modal();
    if (!t || this.gerando()) return;
    this.erro.set('');

    let caminho = '';
    let params: Record<string, string> = {};
    switch (t) {
      case 'maquina':
        if (!this.rMaquinaId) { this.erro.set('Escolha a máquina.'); return; }
        caminho = `/pdf/maquina/${this.rMaquinaId}`;
        break;
      case 'servico':
        if (this.rServicoModo === 'periodo') {
          caminho = '/pdf/servicos-periodo';
          params = { de: this.rDe, ate: this.rAte };
        } else {
          if (!this.rServicoId) { this.erro.set('Escolha o serviço.'); return; }
          caminho = `/pdf/servico/${this.rServicoId}`;
        }
        break;
      case 'periodo':
        caminho = '/pdf/periodo';
        params = { de: this.rDe, ate: this.rAte };
        break;
      case 'ajudantes':
        caminho = '/pdf/ajudantes';
        params = { de: this.rDe, ate: this.rAte };
        if (this.rAjudanteId) params['ajudante_id'] = this.rAjudanteId;
        break;
      case 'entradas':
        caminho = '/pdf/entradas';
        params = { de: this.rDe, ate: this.rAte };
        break;
      case 'resultado':
        caminho = '/pdf/resultado';
        params = { de: this.rDe, ate: this.rAte };
        break;
      case 'fechamento':
        if (this.rModoFech === 'registrado') {
          if (!this.rFechamentoId) { this.erro.set('Nenhum fechamento registrado ainda — use a prévia.'); return; }
          caminho = `/pdf/fechamento/${this.rFechamentoId}`;
        } else {
          caminho = '/pdf/fechamento-previa';
          params = { de: this.rDe, ate: this.rAte };
        }
        break;
    }

    this.gerando.set(true);
    this.api.getBlob(caminho, params).subscribe({
      next: (blob) => {
        this.gerando.set(false);
        this.modal.set(null);
        window.open(URL.createObjectURL(blob), '_blank');
      },
      error: () => {
        this.gerando.set(false);
        this.erro.set('Não foi possível gerar o PDF (confira os parâmetros).');
      },
    });
  }
}
