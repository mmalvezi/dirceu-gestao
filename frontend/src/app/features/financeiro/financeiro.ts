import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { Icon } from '../../core/icon';
import { ORIGEM_CHIP } from '../../core/labels';
import {
  FinanceiroTotais,
  Maquina,
  Pagamento,
  Recebimento,
  RepasseEntrada,
} from '../../core/models';
import { FinanceiroService } from '../../core/services/financeiro.service';
import { MaquinaService } from '../../core/services/maquina.service';
import { formatDate, formatHours, formatMoney, primeiroDiaMesIso, todayIso } from '../../core/format';
import { Modal } from '../../shared/modal';

type Aba = 'receb' | 'pagto' | 'acerto';

/** Financeiro com 3 abas (scrFinanceiro do protótipo). Aba na URL (?aba=). */
@Component({
  selector: 'app-financeiro',
  imports: [FormsModule, Modal, Icon],
  templateUrl: './financeiro.html',
})
export class FinanceiroPage implements OnInit {
  private svc = inject(FinanceiroService);
  private maquinasSvc = inject(MaquinaService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  fmtMoney = formatMoney;
  fmtData = formatDate;
  fmtHoras = formatHours;
  chip = ORIGEM_CHIP;

  aba = signal<Aba>('receb');
  de = primeiroDiaMesIso();
  ate = todayIso();

  // Recebimentos
  tipoFiltro = '';
  recebs = signal<Recebimento[]>([]);
  // Pagos a ajudantes
  origemFiltro = '';
  pagamentos = signal<Pagamento[]>([]);
  // Acerto & origens
  totais = signal<FinanceiroTotais | null>(null);
  verbas = signal<RepasseEntrada[]>([]);

  // Modal adiantamento
  adAberto = signal(false);
  adEdit: Recebimento | null = null;
  adData = todayIso();
  adValor: string | number | null = '';
  adMaquinaId = '';
  adObs = '';
  adErro = signal('');
  maquinasAbertas = signal<Maquina[]>([]);

  // Modal verba de repasse
  vbAberto = signal(false);
  vbEdit: RepasseEntrada | null = null;
  vbData = todayIso();
  vbValor: string | number | null = '';
  vbObs = '';
  vbErro = signal('');

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((qp) => {
      const aba = qp.get('aba') as Aba | null;
      if (aba && ['receb', 'pagto', 'acerto'].includes(aba) && aba !== this.aba()) {
        this.aba.set(aba);
        this.recarregar();
      }
    });
  }

  ngOnInit(): void {
    const aba = this.route.snapshot.queryParamMap.get('aba') as Aba | null;
    if (aba && ['receb', 'pagto', 'acerto'].includes(aba)) this.aba.set(aba);
    this.recarregar();
    this.maquinasSvc.listar().subscribe((ms) =>
      this.maquinasAbertas.set(ms.filter((m) => m.status !== 'fechada')),
    );
  }

  setAba(a: Aba): void {
    this.aba.set(a);
    this.router.navigate([], { queryParams: { aba: a }, queryParamsHandling: 'merge' });
    this.recarregar();
  }

  recarregar(): void {
    const a = this.aba();
    if (a === 'receb') {
      this.svc
        .recebimentos({ tipo: this.tipoFiltro || undefined, de: this.de, ate: this.ate })
        .subscribe((r) => this.recebs.set(r));
    } else if (a === 'pagto') {
      this.svc
        .pagamentos({ de: this.de, ate: this.ate, origem: this.origemFiltro || undefined })
        .subscribe((p) => this.pagamentos.set(p));
    } else {
      this.svc.totais(this.de, this.ate).subscribe((t) => this.totais.set(t));
      this.svc.repasses(this.de, this.ate).subscribe((v) => this.verbas.set(v));
    }
  }

  editavel(r: Recebimento): boolean {
    return r.tipo === 'adiantamento' && r.status === 'aberto';
  }

  // ---- modal adiantamento ----

  abrirAdiantamento(r: Recebimento | null): void {
    this.adEdit = r;
    this.adData = r?.data ?? todayIso();
    this.adValor = r ? r.valor : '';
    this.adMaquinaId = r?.maquina_id != null ? String(r.maquina_id) : '';
    this.adObs = r?.obs ?? '';
    this.adErro.set('');
    this.adAberto.set(true);
  }

  salvarAdiantamento(): void {
    const valor = Number(String(this.adValor ?? '').trim());
    if (!(valor > 0)) {
      this.adErro.set('Informe um valor maior que zero.');
      return;
    }
    const dados = {
      data: this.adData,
      valor,
      maquina_id: this.adMaquinaId ? Number(this.adMaquinaId) : null,
      obs: this.adObs.trim() || null,
    };
    const req = this.adEdit
      ? this.svc.atualizarRecebimento(this.adEdit.id, dados)
      : this.svc.criarAdiantamento(dados);
    req.subscribe({
      next: () => {
        this.adAberto.set(false);
        this.recarregar();
      },
      error: (e: HttpErrorResponse) => {
        const d = e.error?.detail;
        this.adErro.set(typeof d === 'string' ? d : 'Não foi possível salvar.');
      },
    });
  }

  excluirRecebimento(r: Recebimento): void {
    if (!confirm(`Excluir o adiantamento de ${formatMoney(r.valor)}?`)) return;
    this.svc.excluirRecebimento(r.id).subscribe(() => this.recarregar());
  }

  // ---- modal verba de repasse ----

  abrirVerba(v: RepasseEntrada | null): void {
    this.vbEdit = v;
    this.vbData = v?.data ?? todayIso();
    this.vbValor = v ? v.valor : '';
    this.vbObs = v?.obs ?? '';
    this.vbErro.set('');
    this.vbAberto.set(true);
  }

  salvarVerba(): void {
    const valor = Number(String(this.vbValor ?? '').trim());
    if (!(valor > 0)) {
      this.vbErro.set('Informe um valor maior que zero.');
      return;
    }
    const dados = { data: this.vbData, valor, obs: this.vbObs.trim() || null };
    const req = this.vbEdit
      ? this.svc.atualizarRepasse(this.vbEdit.id, dados)
      : this.svc.criarRepasse(dados);
    req.subscribe({
      next: () => {
        this.vbAberto.set(false);
        this.recarregar();
      },
      error: (e: HttpErrorResponse) => {
        const d = e.error?.detail;
        this.vbErro.set(typeof d === 'string' ? d : 'Não foi possível salvar.');
      },
    });
  }

  excluirVerba(v: RepasseEntrada): void {
    if (!confirm(`Excluir a verba de repasse de ${formatMoney(v.valor)}?`)) return;
    this.svc.excluirRepasse(v.id).subscribe(() => this.recarregar());
  }
}
