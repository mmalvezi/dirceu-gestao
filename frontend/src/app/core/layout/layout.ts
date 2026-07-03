import { Component, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { filter } from 'rxjs';

import { AuthService } from '../auth.service';
import { Icon, IconName } from '../icon';

interface NavItem {
  path: string;
  label: string;
  icon: IconName;
  exact: boolean;
}

/** Layout do protótipo: sidebar ferro no desktop, tabbar no mobile, FAB laranja. */
@Component({
  selector: 'app-layout',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon],
  templateUrl: './layout.html',
})
export class Layout {
  private auth = inject(AuthService);
  private router = inject(Router);

  nav: NavItem[] = [
    { path: '/', label: 'Início', icon: 'home', exact: true },
    { path: '/maquinas', label: 'Máquinas', icon: 'mach', exact: false },
    { path: '/financeiro', label: 'Financeiro', icon: 'fin', exact: false },
    { path: '/fechamento', label: 'Fechamento', icon: 'fech', exact: false },
    { path: '/relatorios', label: 'Relatórios', icon: 'rep', exact: false },
  ];

  hojeChip = this.chipDeHoje();
  private url = signal(this.router.url);

  constructor() {
    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntilDestroyed(),
      )
      .subscribe((e) => this.url.set(e.urlAfterRedirects));
  }

  /** FAB visível nas telas de máquinas (como no protótipo). */
  get mostraFab(): boolean {
    return this.url().startsWith('/maquinas');
  }

  lancarDia(): void {
    // Placeholder — a Fase 12a liga o FAB no modal "Lançar dia".
    console.log('[FAB] Lançar dia — implementado na Fase 12a');
  }

  sair(): void {
    this.auth.logout();
  }

  private chipDeHoje(): string {
    const dias = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];
    const d = new Date();
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    return `${dias[d.getDay()]}, ${dd}/${mm}`;
  }
}
