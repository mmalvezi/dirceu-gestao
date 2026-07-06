import { Routes } from '@angular/router';

import { authGuard } from './core/auth.guard';
import { Layout } from './core/layout/layout';

export const routes: Routes = [
  {
    path: 'login',
    title: 'Entrar — Dirceu',
    loadComponent: () => import('./features/login/login').then((m) => m.Login),
  },
  {
    path: '',
    component: Layout,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        title: 'Início — Dirceu',
        loadComponent: () => import('./features/inicio/inicio').then((m) => m.InicioPage),
      },
      {
        path: 'maquinas',
        title: 'Máquinas — Dirceu',
        loadComponent: () => import('./features/maquinas/maquinas').then((m) => m.MaquinasPage),
      },
      {
        path: 'maquinas/:id',
        title: 'Máquina — Dirceu',
        loadComponent: () =>
          import('./features/maquinas/maquina-detalhe').then((m) => m.MaquinaDetalhePage),
      },
      {
        path: 'servicos',
        title: 'Serviços — Dirceu',
        loadComponent: () => import('./features/servicos/servicos').then((m) => m.ServicosPage),
      },
      {
        path: 'servicos/:id',
        title: 'Serviço — Dirceu',
        loadComponent: () =>
          import('./features/servicos/servico-detalhe').then((m) => m.ServicoDetalhePage),
      },
      {
        path: 'financeiro',
        title: 'Financeiro — Dirceu',
        loadComponent: () => import('./features/financeiro/financeiro').then((m) => m.FinanceiroPage),
      },
      {
        path: 'fechamento',
        title: 'Fechamento — Dirceu',
        loadComponent: () => import('./features/fechamento/fechamento').then((m) => m.FechamentoPage),
      },
      {
        path: 'relatorios',
        title: 'Relatórios — Dirceu',
        loadComponent: () => import('./features/relatorios/relatorios').then((m) => m.RelatoriosPage),
      },
      {
        path: 'ajustes',
        title: 'Ajustes — Dirceu',
        loadComponent: () => import('./features/ajustes/ajustes').then((m) => m.AjustesPage),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
