import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { Icon } from '../../core/icon';
import { Fechamento, FechamentoDetalhe, FechamentoPrevia } from '../../core/models';
import { FechamentoService } from '../../core/services/fechamento.service';
import { formatDate, primeiroDiaMesAnteriorIso, todayIso } from '../../core/format';
import { formatMoney } from '../../core/format';
import { Modal } from '../../shared/modal';

/** Fechamento com a EPR: prévia por período, registro do acerto e histórico. */
@Component({
  selector: 'app-fechamento',
  imports: [FormsModule, Modal, Icon],
  templateUrl: './fechamento.html',
})
export class FechamentoPage implements OnInit {
  private svc = inject(FechamentoService);
  private route = inject(ActivatedRoute);

  fmtMoney = formatMoney;
  fmtData = formatDate;

  de = primeiroDiaMesAnteriorIso();
  ate = todayIso();

  previa = signal<FechamentoPrevia | null>(null);
  calculando = signal(false);
  erro = signal('');

  confirmAberto = signal(false);
  obs = '';
  registrando = signal(false);
  sucesso = signal<FechamentoDetalhe | null>(null);

  hist = signal<Fechamento[]>([]);
  detalhe = signal<FechamentoDetalhe | null>(null); // expansão no histórico

  ngOnInit(): void {
    // /fechamento?de=X&ate=Y pré-preenche e já calcula (links do dashboard/detalhe).
    const qp = this.route.snapshot.queryParamMap;
    if (qp.get('de') && qp.get('ate')) {
      this.de = qp.get('de')!;
      this.ate = qp.get('ate')!;
      this.calcular();
    }
    this.carregarHist();
  }

  calcular(): void {
    this.erro.set('');
    this.sucesso.set(null);
    this.calculando.set(true);
    this.svc.previa(this.de, this.ate).subscribe({
      next: (p) => {
        this.previa.set(p);
        this.calculando.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.calculando.set(false);
        this.previa.set(null);
        const d = e.error?.detail;
        this.erro.set(typeof d === 'string' ? d : 'Não foi possível calcular a prévia.');
      },
    });
  }

  /** Largura (%) do segmento âmbar (adiantado) da régua. */
  advPct(p: FechamentoPrevia): number {
    if (p.total_devido <= 0) return 0;
    return Math.min((p.total_adiantado / p.total_devido) * 100, 100);
  }

  registrar(): void {
    if (this.registrando()) return;
    this.registrando.set(true);
    this.svc
      .registrar({ periodo_de: this.de, periodo_ate: this.ate, obs: this.obs.trim() || null })
      .subscribe({
        next: (f) => {
          this.registrando.set(false);
          this.confirmAberto.set(false);
          this.obs = '';
          this.sucesso.set(f);
          this.previa.set(null);
          this.carregarHist();
        },
        error: (e: HttpErrorResponse) => {
          this.registrando.set(false);
          this.confirmAberto.set(false);
          const d = e.error?.detail;
          this.erro.set(typeof d === 'string' ? d : 'Não foi possível registrar o acerto.');
        },
      });
  }

  carregarHist(): void {
    this.svc.listar().subscribe((fs) => this.hist.set(fs));
  }

  verDetalhe(f: Fechamento): void {
    if (this.detalhe()?.id === f.id) {
      this.detalhe.set(null); // recolhe
      return;
    }
    this.svc.detalhe(f.id).subscribe((d) => this.detalhe.set(d));
  }

  abrirPdfPrevia(): void {
    this.svc.pdfPrevia(this.de, this.ate).subscribe((b) => {
      window.open(URL.createObjectURL(b), '_blank');
    });
  }

  abrirPdfFechamento(id: number): void {
    this.svc.pdfFechamento(id).subscribe((b) => {
      window.open(URL.createObjectURL(b), '_blank');
    });
  }

  nomesMaquinas(f: Fechamento): string {
    return f.maquinas.map((m) => m.nome).join(', ');
  }
}
