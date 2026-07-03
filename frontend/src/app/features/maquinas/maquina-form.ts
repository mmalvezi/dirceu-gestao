import { Component, OnInit, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';

import { Icon } from '../../core/icon';
import { Maquina } from '../../core/models';
import { MaquinaService } from '../../core/services/maquina.service';
import { todayIso } from '../../core/format';
import { Modal } from '../../shared/modal';

/** Modal Nova/Editar máquina. */
@Component({
  selector: 'app-maquina-form',
  imports: [FormsModule, Modal, Icon],
  template: `
    <app-modal (fechado)="fechado.emit()">
      <h3>{{ maquina() ? 'Editar máquina' : 'Nova máquina' }}</h3>
      <div class="muted">Empreita/projeto dentro da EPR</div>

      @if (erro()) {
        <div class="alert a-hot"><app-icon name="alert" /><div>{{ erro() }}</div></div>
      }

      <div class="f">
        <label>Nome da máquina *</label>
        <input [(ngModel)]="nome" name="nome" placeholder="Ex.: Jato E120" />
      </div>
      <div class="f">
        <label>Cliente *</label>
        <input [(ngModel)]="cliente" name="cliente" placeholder="Ex.: Metalúrgica Santa Fé" />
      </div>
      <div class="f-2">
        <div class="f">
          <label>Empreita (R$) *</label>
          <input type="number" inputmode="decimal" min="0" [(ngModel)]="empreita" name="empreita" />
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
export class MaquinaForm implements OnInit {
  maquina = input<Maquina | null>(null); // presente = edição

  salvo = output<Maquina>();
  fechado = output<void>();

  private svc = inject(MaquinaService);

  erro = signal('');
  salvando = signal(false);

  nome = '';
  cliente = '';
  empreita = '';
  dataInicio = todayIso();
  obs = '';

  ngOnInit(): void {
    const m = this.maquina();
    if (m) {
      this.nome = m.nome;
      this.cliente = m.cliente;
      this.empreita = String(m.empreita);
      this.dataInicio = m.data_inicio;
      this.obs = m.obs ?? '';
    }
  }

  salvar(): void {
    if (this.salvando()) return;
    this.erro.set('');
    const empreita = Number(this.empreita);
    if (!this.nome.trim() || !this.cliente.trim()) {
      this.erro.set('Preencha nome e cliente.');
      return;
    }
    if (!(empreita > 0)) {
      this.erro.set('Informe o valor da empreita.');
      return;
    }
    if (!this.dataInicio) {
      this.erro.set('Informe a data de início.');
      return;
    }

    const dados = {
      nome: this.nome.trim(),
      cliente: this.cliente.trim(),
      empreita,
      data_inicio: this.dataInicio,
      obs: this.obs.trim() || null,
    };
    const m = this.maquina();
    const req = m ? this.svc.atualizar(m.id, dados) : this.svc.criar(dados);

    this.salvando.set(true);
    req.subscribe({
      next: (res) => this.salvo.emit(res),
      error: (err: HttpErrorResponse) => {
        this.salvando.set(false);
        const d = err.error?.detail;
        this.erro.set(typeof d === 'string' ? d : 'Não foi possível salvar a máquina.');
      },
    });
  }
}
