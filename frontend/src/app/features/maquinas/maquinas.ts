import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { FabService } from '../../core/fab.service';
import { STATUS_BADGE, barClass } from '../../core/labels';
import { Maquina } from '../../core/models';
import { MaquinaService } from '../../core/services/maquina.service';
import { formatDateShort, formatHours, formatMoney } from '../../core/format';
import { Modal } from '../../shared/modal';
import { LancarDia } from './lancar-dia';
import { MaquinaForm } from './maquina-form';

const FILTROS: [string, string][] = [
  ['', 'Todas'],
  ['andamento', 'Em andamento'],
  ['finalizada', 'Finalizadas'],
  ['fechada', 'Fechadas'],
];

/** Lista de máquinas (scrMaquinas do protótipo). */
@Component({
  selector: 'app-maquinas',
  imports: [FormsModule, Modal, MaquinaForm, LancarDia],
  templateUrl: './maquinas.html',
})
export class MaquinasPage implements OnInit {
  private svc = inject(MaquinaService);
  private router = inject(Router);
  private fab = inject(FabService);

  FILTROS = FILTROS;
  fmtMoney = formatMoney;
  fmtHoras = formatHours;
  fmtDataCurta = formatDateShort;
  badge = STATUS_BADGE;
  barCls = barClass;

  maquinas = signal<Maquina[]>([]);
  carregou = signal(false);
  filtro = signal('');
  q = '';
  private debounce: ReturnType<typeof setTimeout> | null = null;

  formAberto = signal(false);
  pickerAberto = signal(false);
  lancarEm = signal<Maquina | null>(null);

  constructor() {
    this.fab.cliques.pipe(takeUntilDestroyed()).subscribe(() => this.abrirLancarViaFab());
  }

  ngOnInit(): void {
    this.carregar();
  }

  carregar(): void {
    this.svc.listar(this.filtro() || undefined, this.q.trim() || undefined).subscribe((ms) => {
      this.maquinas.set(ms);
      this.carregou.set(true);
    });
  }

  setFiltro(f: string): void {
    this.filtro.set(f);
    this.carregar();
  }

  buscou(): void {
    if (this.debounce) clearTimeout(this.debounce);
    this.debounce = setTimeout(() => this.carregar(), 300);
  }

  abrir(m: Maquina): void {
    this.router.navigate(['/maquinas', m.id]);
  }

  truncar(s: string, n = 48): string {
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  /** FAB: 1 máquina em andamento -> direto; senão, passo rápido de seleção. */
  private abrirLancarViaFab(): void {
    const abertas = this.maquinas().filter((m) => m.status !== 'fechada');
    const andamento = abertas.filter((m) => m.status === 'andamento');
    if (andamento.length === 1) {
      this.lancarEm.set(andamento[0]);
    } else if (abertas.length > 0) {
      this.pickerAberto.set(true);
    } else {
      this.formAberto.set(true); // nada aberto: convida a criar a primeira máquina
    }
  }

  escolherParaLancar(m: Maquina): void {
    this.pickerAberto.set(false);
    this.lancarEm.set(m);
  }

  lancavel(): Maquina[] {
    return this.maquinas().filter((m) => m.status !== 'fechada');
  }

  aoSalvarMaquina(): void {
    this.formAberto.set(false);
    this.carregar();
  }

  aoLancar(): void {
    this.lancarEm.set(null);
    this.carregar();
  }
}
