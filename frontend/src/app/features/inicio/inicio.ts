import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { Icon } from '../../core/icon';
import { Aviso, Dashboard } from '../../core/models';
import { DashboardService } from '../../core/services/dashboard.service';
import {
  formatHours,
  formatMoney,
  primeiroDiaMesAnteriorIso,
  todayIso,
} from '../../core/format';

/** Início (scrInicio do protótipo): KPIs, avisos acionáveis, horas, margens e resumo. */
@Component({
  selector: 'app-inicio',
  imports: [FormsModule, Icon],
  templateUrl: './inicio.html',
})
export class InicioPage implements OnInit {
  private svc = inject(DashboardService);
  private router = inject(Router);

  fmtMoney = formatMoney;
  fmtHoras = formatHours;

  dash = signal<Dashboard | null>(null);
  copiado = signal(false);
  de = '';
  ate = '';

  ngOnInit(): void {
    this.carregar();
  }

  carregar(): void {
    this.svc.get(this.de || undefined, this.ate || undefined).subscribe((d) => {
      this.dash.set(d);
      this.de = d.periodo.de;
      this.ate = d.periodo.ate;
    });
  }

  /** Altura da barra (%) proporcional ao máximo da semana (hoje = laranja via CSS). */
  alturaBarra(horas: number): number {
    const d = this.dash();
    if (!d || horas <= 0) return 3;
    const max = Math.max(...d.horas_por_dia.map((x) => x.horas), 1);
    return Math.max((horas / max) * 100, 4);
  }

  avisoClasse(a: Aviso): string {
    return { warn: 'a-warn', hot: 'a-hot', info: 'a-info' }[a.nivel] ?? 'a-info';
  }

  avisoClicavel(a: Aviso): boolean {
    return a.tipo === 'fechamento_pendente' || (a.tipo === 'custo_alto' && a.maquina_id != null);
  }

  clicarAviso(a: Aviso): void {
    if (a.tipo === 'fechamento_pendente') {
      // Período generoso (mês passado -> hoje) pra prévia já vir calculada.
      this.router.navigate(['/fechamento'], {
        queryParams: { de: primeiroDiaMesAnteriorIso(), ate: todayIso() },
      });
    } else if (a.tipo === 'custo_alto' && a.maquina_id != null) {
      this.router.navigate(['/maquinas', a.maquina_id]);
    }
  }

  abrirMaquina(id: number): void {
    this.router.navigate(['/maquinas', id]);
  }

  copiar(): void {
    const d = this.dash();
    if (!d) return;
    navigator.clipboard.writeText(d.resumo_whatsapp).then(() => {
      this.copiado.set(true);
      setTimeout(() => this.copiado.set(false), 1600);
    });
  }

  waHref(): string {
    const d = this.dash();
    return d ? 'https://wa.me/?text=' + encodeURIComponent(d.resumo_whatsapp) : '#';
  }

  subPago(d: Dashboard): { repasse: string; bolso: string; epr: string } {
    const p = d.kpis.pago_ajudantes;
    return {
      repasse: formatMoney(p.repasse),
      bolso: formatMoney(p.bolso),
      epr: p.epr_direto > 0 ? formatMoney(p.epr_direto) : '',
    };
  }

  nomesAReceber(d: Dashboard): string {
    return d.kpis.a_receber.maquinas.map((m) => m.nome).join(', ') || '—';
  }

  barraClasse(pct: number): string {
    return pct > 70 ? 'hot' : pct > 45 ? '' : 'ok';
  }
}
