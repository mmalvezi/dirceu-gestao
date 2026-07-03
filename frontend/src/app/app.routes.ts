import { Routes } from '@angular/router';

import { authGuard } from './core/auth.guard';
import { Layout } from './core/layout/layout';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/login/login').then((m) => m.Login),
  },
  {
    path: '',
    component: Layout,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () => import('./features/inicio/inicio').then((m) => m.InicioPage),
      },
      {
        path: 'maquinas',
        loadComponent: () => import('./features/maquinas/maquinas').then((m) => m.MaquinasPage),
      },
      {
        path: 'maquinas/:id',
        loadComponent: () =>
          import('./features/maquinas/maquina-detalhe').then((m) => m.MaquinaDetalhePage),
      },
      {
        path: 'financeiro',
        loadComponent: () => import('./features/financeiro/financeiro').then((m) => m.FinanceiroPage),
      },
      {
        path: 'fechamento',
        loadComponent: () => import('./features/fechamento/fechamento').then((m) => m.FechamentoPage),
      },
      {
        path: 'relatorios',
        loadComponent: () => import('./features/relatorios/relatorios').then((m) => m.RelatoriosPage),
      },
      {
        path: 'ajustes',
        loadComponent: () => import('./features/ajustes/ajustes').then((m) => m.AjustesPage),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
