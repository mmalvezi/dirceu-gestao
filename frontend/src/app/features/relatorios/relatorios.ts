import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/api.service';
import { Icon } from '../../core/icon';
import { Ajudante, Fechamento, Maquina } from '../../core/models';
import { AjudanteService } from '../../core/services/ajudante.service';
import { FechamentoService } from '../../core/services/fechamento.service';
import { MaquinaService } from '../../core/services/maquina.service';
import { formatDate, primeiroDiaMesIso, todayIso } from '../../core/format';
import { Modal } from '../../shared/modal';

type TipoRel = 'maquina' | 'periodo' | 'ajudantes' | 'entradas' | 'fechamento';

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
  private ajudantesSvc = inject(AjudanteService);
  private fechamentosSvc = inject(FechamentoService);

  fmtData = formatDate;

  CARDS: CardRel[] = [
    { tipo: 'maquina', titulo: 'Relatório por máquina', desc: 'Diário completo, custos, horas e margem de uma máquina.' },
    { tipo: 'periodo', titulo: 'Relatório do período (todas)', desc: 'Tudo que rodou no período, consolidado máquina a máquina.' },
    { tipo: 'ajudantes', titulo: 'Saídas — ajudantes', desc: 'Quanto cada ajudante recebeu, com a origem de cada pagamento.' },
    { tipo: 'entradas', titulo: 'Entradas — recebimentos', desc: 'Adiantamentos e fechamentos recebidos da EPR.' },
    { tipo: 'fechamento', titulo: 'Fechamento', desc: 'O confronto: finalizado no período × adiantado. Pronto pra apresentar.' },
  ];

  maquinas = signal<Maquina[]>([]);
  ajudantes = signal<Ajudante[]>([]);
  fechamentos = signal<Fechamento[]>([]);

  modal = signal<TipoRel | null>(null);
  erro = signal('');
  gerando = signal(false);

  // parâmetros
  rMaquinaId = '';
  rDe = primeiroDiaMesIso();
  rAte = todayIso();
  rAjudanteId = '';
  rFechamentoId = '';
  rModoFech: 'registrado' | 'previa' = 'registrado';

  ngOnInit(): void {
    this.maquinasSvc.listar().subscribe((ms) => this.maquinas.set(ms));
    this.ajudantesSvc.listar(true).subscribe((as) => this.ajudantes.set(as));
    this.fechamentosSvc.listar().subscribe((fs) => {
      this.fechamentos.set(fs);
      if (fs.length) this.rFechamentoId = String(fs[0].id);
    });
  }

  abrir(tipo: TipoRel): void {
    this.erro.set('');
    if (tipo === 'maquina' && this.maquinas().length && !this.rMaquinaId) {
      this.rMaquinaId = String(this.maquinas()[0].id);
    }
    this.modal.set(tipo);
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
