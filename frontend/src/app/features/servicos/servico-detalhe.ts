import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { FabService } from '../../core/fab.service';
import { Icon } from '../../core/icon';
import { ORIGEM_CHIP, STATUS_SERVICO, barClass } from '../../core/labels';
import { ServicoDetalhe, ServicoEntrada } from '../../core/models';
import { ServicoService } from '../../core/services/servico.service';
import { formatDateDia, formatHours, formatMoney } from '../../core/format';
import { Modal } from '../../shared/modal';
import { Voltar } from '../../shared/voltar';
import { LancarDia } from '../maquinas/lancar-dia';
import { ServicoForm } from './servico-form';

/** Detalhe do serviço avulso com diário (análogo ao detalhe de máquina). */
@Component({
  selector: 'app-servico-detalhe',
  imports: [Icon, LancarDia, ServicoForm, Modal, Voltar],
  templateUrl: './servico-detalhe.html',
})
export class ServicoDetalhePage implements OnInit {
  private svc = inject(ServicoService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private fab = inject(FabService);

  fmtMoney = formatMoney;
  fmtHoras = formatHours;
  fmtDia = formatDateDia;
  badge = STATUS_SERVICO;
  chip = ORIGEM_CHIP;
  barCls = barClass;

  id = 0;
  s = signal<ServicoDetalhe | null>(null);
  aviso = signal('');
  lancarAberto = signal(false);
  editarEntrada = signal<ServicoEntrada | null>(null);
  editarServico = signal(false);
  excluirAberto = signal(false);
  excluindo = signal(false);
  private avisoTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.fab.cliques.pipe(takeUntilDestroyed()).subscribe(() => {
      if (this.s()?.status !== 'fechado') this.lancarAberto.set(true);
    });
  }

  ngOnInit(): void {
    this.id = Number(this.route.snapshot.paramMap.get('id'));
    this.carregar();
  }

  carregar(): void {
    this.svc.detalhe(this.id).subscribe({
      next: (det) => this.s.set(det),
      error: () => this.router.navigate(['/servicos']),
    });
  }

  aoSalvarDia(res: ServicoEntrada): void {
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

  excluirEntrada(e: ServicoEntrada): void {
    if (!confirm(`Excluir o lançamento de ${formatDateDia(e.data)}?`)) return;
    this.svc.excluirEntrada(this.id, e.id).subscribe(() => this.carregar());
  }

  finalizar(): void {
    if (!confirm('Finalizar este serviço? Ele entra na fila do próximo fechamento.')) return;
    this.svc.atualizar(this.id, { status: 'finalizado' }).subscribe(() => this.carregar());
  }

  reabrir(): void {
    this.svc.atualizar(this.id, { status: 'aberto' }).subscribe(() => this.carregar());
  }

  abrirPdf(): void {
    this.svc.pdf(this.id).subscribe((blob) => {
      window.open(URL.createObjectURL(blob), '_blank');
    });
  }

  confirmarExclusao(): void {
    if (this.excluindo()) return;
    this.excluindo.set(true);
    this.svc.excluir(this.id).subscribe({
      next: () => this.router.navigate(['/servicos']),
      error: () => {
        this.excluindo.set(false);
        this.excluirAberto.set(false);
      },
    });
  }
}
