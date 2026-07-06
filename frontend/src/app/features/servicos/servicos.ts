import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { FabService } from '../../core/fab.service';
import { STATUS_SERVICO, barClass } from '../../core/labels';
import { Servico } from '../../core/models';
import { ServicoService } from '../../core/services/servico.service';
import { formatDateShort, formatHours, formatMoney } from '../../core/format';
import { Modal } from '../../shared/modal';
import { LancarDia } from '../maquinas/lancar-dia';
import { ServicoForm } from './servico-form';

const FILTROS: [string, string][] = [
  ['', 'Todos'],
  ['aberto', 'Abertos'],
  ['finalizado', 'Finalizados'],
  ['fechado', 'Fechados'],
];

/** Lista de serviços avulsos (irmã da lista de máquinas). */
@Component({
  selector: 'app-servicos',
  imports: [FormsModule, Modal, ServicoForm, LancarDia, RouterLink, RouterLinkActive],
  templateUrl: './servicos.html',
})
export class ServicosPage implements OnInit {
  private svc = inject(ServicoService);
  private router = inject(Router);
  private fab = inject(FabService);

  FILTROS = FILTROS;
  fmtMoney = formatMoney;
  fmtHoras = formatHours;
  fmtDataCurta = formatDateShort;
  badge = STATUS_SERVICO;
  barCls = barClass;

  servicos = signal<Servico[]>([]);
  carregou = signal(false);
  filtro = signal('');
  q = '';
  private debounce: ReturnType<typeof setTimeout> | null = null;

  formAberto = signal(false);
  pickerAberto = signal(false);
  lancarEm = signal<Servico | null>(null);

  constructor() {
    this.fab.cliques.pipe(takeUntilDestroyed()).subscribe(() => this.abrirLancarViaFab());
  }

  ngOnInit(): void {
    this.carregar();
  }

  carregar(): void {
    this.svc.listar(this.filtro() || undefined, this.q.trim() || undefined).subscribe((ss) => {
      this.servicos.set(ss);
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

  abrir(s: Servico): void {
    this.router.navigate(['/servicos', s.id]);
  }

  truncar(s: string, n = 48): string {
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  private abrirLancarViaFab(): void {
    const abertos = this.servicos().filter((s) => s.status !== 'fechado');
    const abertosAtivos = abertos.filter((s) => s.status === 'aberto');
    if (abertosAtivos.length === 1) {
      this.lancarEm.set(abertosAtivos[0]);
    } else if (abertos.length > 0) {
      this.pickerAberto.set(true);
    } else {
      this.formAberto.set(true);
    }
  }

  escolherParaLancar(s: Servico): void {
    this.pickerAberto.set(false);
    this.lancarEm.set(s);
  }

  lancavel(): Servico[] {
    return this.servicos().filter((s) => s.status !== 'fechado');
  }

  aoSalvarServico(): void {
    this.formAberto.set(false);
    this.carregar();
  }

  aoLancar(): void {
    this.lancarEm.set(null);
    this.carregar();
  }
}
