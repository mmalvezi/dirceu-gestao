import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { FabService } from '../../core/fab.service';
import { Icon } from '../../core/icon';
import { ORIGEM_CHIP, STATUS_BADGE, barClass } from '../../core/labels';
import { DiarioEntrada, MaquinaDetalhe } from '../../core/models';
import { MaquinaService } from '../../core/services/maquina.service';
import { formatDateDia, formatHours, formatMoney } from '../../core/format';
import { Voltar } from '../../shared/voltar';
import { LancarDia } from './lancar-dia';
import { MaquinaForm } from './maquina-form';

/** Detalhe da máquina com diário de obra (scrMaquina do protótipo). */
@Component({
  selector: 'app-maquina-detalhe',
  imports: [Icon, LancarDia, MaquinaForm, Voltar],
  templateUrl: './maquina-detalhe.html',
})
export class MaquinaDetalhePage implements OnInit {
  private svc = inject(MaquinaService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private fab = inject(FabService);

  fmtMoney = formatMoney;
  fmtHoras = formatHours;
  fmtDia = formatDateDia;
  badge = STATUS_BADGE;
  chip = ORIGEM_CHIP;
  barCls = barClass;

  id = 0;
  m = signal<MaquinaDetalhe | null>(null);
  aviso = signal('');
  lancarAberto = signal(false);
  editarEntrada = signal<DiarioEntrada | null>(null);
  editarMaquina = signal(false);
  private avisoTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.fab.cliques.pipe(takeUntilDestroyed()).subscribe(() => {
      if (this.m()?.status !== 'fechada') this.lancarAberto.set(true);
    });
  }

  ngOnInit(): void {
    this.id = Number(this.route.snapshot.paramMap.get('id'));
    this.carregar();
  }

  carregar(): void {
    this.svc.detalhe(this.id).subscribe({
      next: (det) => this.m.set(det),
      error: () => this.router.navigate(['/maquinas']),
    });
  }

  aoSalvarDia(res: DiarioEntrada): void {
    this.lancarAberto.set(false);
    this.editarEntrada.set(null);
    if (res.aviso) this.mostrarAviso(res.aviso);
    this.carregar();
  }

  private mostrarAviso(texto: string): void {
    this.aviso.set(texto);
    if (this.avisoTimer) clearTimeout(this.avisoTimer);
    this.avisoTimer = setTimeout(() => this.aviso.set(''), 7000);
  }

  excluirEntrada(e: DiarioEntrada): void {
    if (!confirm(`Excluir o lançamento de ${formatDateDia(e.data)}?`)) return;
    this.svc.excluirEntrada(this.id, e.id).subscribe(() => this.carregar());
  }

  finalizar(): void {
    if (!confirm('Finalizar esta máquina? Ela entra na fila do próximo fechamento.')) return;
    this.svc.atualizar(this.id, { status: 'finalizada' }).subscribe(() => this.carregar());
  }

  reabrir(): void {
    this.svc.atualizar(this.id, { status: 'andamento' }).subscribe(() => this.carregar());
  }

  abrirPdf(): void {
    this.svc.pdf(this.id).subscribe((blob) => {
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    });
  }
}
