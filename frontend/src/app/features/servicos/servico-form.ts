import { Component, OnInit, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';

import { Icon } from '../../core/icon';
import { Servico } from '../../core/models';
import { ServicoService } from '../../core/services/servico.service';
import { todayIso } from '../../core/format';
import { Modal } from '../../shared/modal';

/** Modal Novo/Editar serviço avulso. */
@Component({
  selector: 'app-servico-form',
  imports: [FormsModule, Modal, Icon],
  template: `
    <app-modal (fechado)="fechado.emit()">
      <h3>{{ servico() ? 'Editar serviço' : 'Novo serviço avulso' }}</h3>
      <div class="muted">Trabalho pontual que você recebe (não é empreita de máquina)</div>

      @if (erro()) {
        <div class="alert a-hot"><app-icon name="alert" /><div>{{ erro() }}</div></div>
      }

      <div class="f">
        <label>O que é o serviço *</label>
        <input [(ngModel)]="descricao" name="descricao" placeholder="Ex.: Reparo da peça X" />
      </div>
      <div class="f">
        <label>Cliente</label>
        <input [(ngModel)]="cliente" name="cliente" placeholder="Ex.: Metalúrgica Santa Fé (opcional)" />
      </div>
      <div class="f-2">
        <div class="f">
          <label>Valor combinado (R$) *</label>
          <input type="number" inputmode="decimal" min="0" [(ngModel)]="valor" name="valor" />
        </div>
        <div class="f">
          <label>Início *</label>
          <input type="date" [(ngModel)]="dataInicio" name="dataInicio" />
        </div>
      </div>
      <div class="f">
        <label>Observações</label>
        <textarea rows="2" [(ngModel)]="obs" name="obs"></textarea>
      </div>

      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">
        <button type="button" class="btn btn-o" (click)="fechado.emit()">Cancelar</button>
        <button type="button" class="btn btn-p" (click)="salvar()" [disabled]="salvando()">
          {{ salvando() ? 'Salvando…' : 'Salvar' }}
        </button>
      </div>
    </app-modal>
  `,
})
export class ServicoForm implements OnInit {
  servico = input<Servico | null>(null);

  salvo = output<Servico>();
  fechado = output<void>();

  private svc = inject(ServicoService);

  erro = signal('');
  salvando = signal(false);

  descricao = '';
  cliente = '';
  valor = '';
  dataInicio = todayIso();
  obs = '';

  ngOnInit(): void {
    const s = this.servico();
    if (s) {
      this.descricao = s.descricao;
      this.cliente = s.cliente ?? '';
      this.valor = String(s.valor);
      this.dataInicio = s.data_inicio;
      this.obs = s.obs ?? '';
    }
  }

  salvar(): void {
    if (this.salvando()) return;
    this.erro.set('');
    const valor = Number(this.valor);
    if (!this.descricao.trim()) {
      this.erro.set('Descreva o serviço.');
      return;
    }
    if (!(valor > 0)) {
      this.erro.set('Informe o valor combinado.');
      return;
    }
    if (!this.dataInicio) {
      this.erro.set('Informe a data de início.');
      return;
    }

    const dados = {
      descricao: this.descricao.trim(),
      cliente: this.cliente.trim() || null,
      valor,
      data_inicio: this.dataInicio,
      obs: this.obs.trim() || null,
    };
    const s = this.servico();
    const req = s ? this.svc.atualizar(s.id, dados) : this.svc.criar(dados);

    this.salvando.set(true);
    req.subscribe({
      next: (res) => this.salvo.emit(res),
      error: (err: HttpErrorResponse) => {
        this.salvando.set(false);
        const d = err.error?.detail;
        this.erro.set(typeof d === 'string' ? d : 'Não foi possível salvar o serviço.');
      },
    });
  }
}
