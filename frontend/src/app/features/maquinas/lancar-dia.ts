import { Component, OnInit, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';

import { Icon } from '../../core/icon';
import { ORIGEM_CHIP } from '../../core/labels';
import { Ajudante, DiarioEntrada, Origem } from '../../core/models';
import { AjudanteService } from '../../core/services/ajudante.service';
import { EntradaPayload, MaquinaService } from '../../core/services/maquina.service';
import { todayIso } from '../../core/format';
import { Modal } from '../../shared/modal';

interface Linha {
  sel: string; // id do ajudante como string, ou 'outro'
  nome: string;
  // input[type=number] com ngModel entrega number|null (NumberValueAccessor)
  horas: string | number | null;
  valor: string | number | null;
  origem: Origem;
  valorManual: boolean; // usuário digitou o valor — não sobrescrever com sugestão
}

/** Modal "Lançar dia" — o coração do sistema (cria/edita entrada do diário). */
@Component({
  selector: 'app-lancar-dia',
  imports: [FormsModule, Modal, Icon],
  templateUrl: './lancar-dia.html',
})
export class LancarDia implements OnInit {
  maquinaId = input.required<number>();
  maquinaNome = input('');
  maquinaCliente = input('');
  entrada = input<DiarioEntrada | null>(null); // presente = edição

  salvo = output<DiarioEntrada>();
  fechado = output<void>();

  private maquinas = inject(MaquinaService);
  private ajudantesSvc = inject(AjudanteService);

  ORIGENS: [Origem, string, string][] = (['repasse', 'epr_direto', 'bolso'] as Origem[]).map(
    (o) => [o, ORIGEM_CHIP[o][0], ORIGEM_CHIP[o][1]],
  );

  ajudantes = signal<Ajudante[]>([]);
  erro = signal('');
  salvando = signal(false);

  data = todayIso();
  descricao = '';
  // signal: em zoneless, o callback do HTTP só re-renderiza se o template depender de um signal
  linhas = signal<Linha[]>([]);

  ngOnInit(): void {
    this.ajudantesSvc.listar(true).subscribe((lista) => {
      this.ajudantes.set(lista);
      const e = this.entrada();
      if (e) {
        this.data = e.data;
        this.descricao = e.descricao;
        this.linhas.set(
          e.trabalhos.map((t) => ({
            sel:
              t.ajudante_id !== null && lista.some((a) => a.id === t.ajudante_id)
                ? String(t.ajudante_id)
                : 'outro',
            nome: t.ajudante_nome,
            horas: String(t.horas),
            valor: String(t.valor),
            origem: t.origem,
            valorManual: true, // edição: preserva os valores gravados
          })),
        );
      } else {
        this.linhas.set([this.novaLinha()]);
      }
    });
  }

  private novaLinha(): Linha {
    return { sel: '', nome: '', horas: '', valor: '', origem: 'repasse', valorManual: false };
  }

  addLinha(): void {
    this.linhas.update((a) => [...a, this.novaLinha()]);
  }

  removeLinha(i: number): void {
    if (this.linhas().length > 1) this.linhas.update((a) => a.filter((_, j) => j !== i));
  }

  /** horas × valor_hora_padrao quando o valor não foi editado manualmente. */
  sugerirValor(l: Linha): void {
    if (l.valorManual || l.sel === 'outro' || !l.sel) return;
    const aj = this.ajudantes().find((a) => a.id === Number(l.sel));
    const horas = Number(l.horas);
    if (aj?.valor_hora_padrao && horas > 0) {
      const v = horas * aj.valor_hora_padrao;
      l.valor = Number.isInteger(v) ? String(v) : v.toFixed(2);
    }
  }

  valorDigitado(l: Linha): void {
    l.valorManual = String(l.valor ?? '').trim() !== '';
  }

  salvar(): void {
    if (this.salvando()) return;
    this.erro.set('');

    if (!this.descricao.trim()) {
      this.erro.set('Descreva o que foi feito.');
      return;
    }
    const trabalhos = [];
    for (const l of this.linhas()) {
      const valorStr = String(l.valor ?? '').trim();
      const horas = Number(l.horas);
      const valor = Number(valorStr);
      if (!l.sel) {
        this.erro.set('Escolha o ajudante em todas as linhas (ou "Outro").');
        return;
      }
      if (l.sel === 'outro' && !l.nome.trim()) {
        this.erro.set('Digite o nome do ajudante avulso.');
        return;
      }
      if (!(horas > 0)) {
        this.erro.set('Horas devem ser maiores que zero.');
        return;
      }
      if (valorStr === '' || !(valor >= 0)) {
        this.erro.set('Informe o valor pago (pode ser 0).');
        return;
      }
      trabalhos.push({
        ajudante_id: l.sel === 'outro' ? null : Number(l.sel),
        ajudante_nome: l.sel === 'outro' ? l.nome.trim() : null,
        horas,
        valor,
        origem: l.origem,
      });
    }

    const payload: EntradaPayload = { data: this.data, descricao: this.descricao.trim(), trabalhos };
    const e = this.entrada();
    const req = e
      ? this.maquinas.atualizarEntrada(this.maquinaId(), e.id, payload)
      : this.maquinas.criarEntrada(this.maquinaId(), payload);

    this.salvando.set(true);
    req.subscribe({
      next: (res) => this.salvo.emit(res),
      error: (err: HttpErrorResponse) => {
        this.salvando.set(false);
        const d = err.error?.detail;
        this.erro.set(typeof d === 'string' ? d : 'Não foi possível salvar o lançamento.');
      },
    });
  }
}
