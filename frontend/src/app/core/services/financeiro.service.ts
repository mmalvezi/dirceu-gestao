import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../api.service';
import { FinanceiroTotais, Pagamento, Recebimento, RepasseEntrada } from '../models';

export interface RecebimentoPayload {
  data?: string;
  valor?: number;
  maquina_id?: number | null;
  obs?: string | null;
}

export interface RepassePayload {
  data?: string;
  valor?: number;
  obs?: string | null;
}

@Injectable({ providedIn: 'root' })
export class FinanceiroService {
  private api = inject(ApiService);

  // ---- recebimentos ----

  recebimentos(f: {
    tipo?: string;
    status?: string;
    de?: string;
    ate?: string;
    maquina_id?: number;
  }): Observable<Recebimento[]> {
    return this.api.get<Recebimento[]>('/recebimentos', f);
  }

  criarAdiantamento(dados: RecebimentoPayload): Observable<Recebimento> {
    return this.api.post<Recebimento>('/recebimentos', dados);
  }

  atualizarRecebimento(id: number, dados: RecebimentoPayload): Observable<Recebimento> {
    return this.api.put<Recebimento>(`/recebimentos/${id}`, dados);
  }

  excluirRecebimento(id: number): Observable<void> {
    return this.api.delete<void>(`/recebimentos/${id}`);
  }

  // ---- verbas de repasse ----

  repasses(de?: string, ate?: string): Observable<RepasseEntrada[]> {
    return this.api.get<RepasseEntrada[]>('/repasses', { de, ate });
  }

  criarRepasse(dados: RepassePayload): Observable<RepasseEntrada> {
    return this.api.post<RepasseEntrada>('/repasses', dados);
  }

  atualizarRepasse(id: number, dados: RepassePayload): Observable<RepasseEntrada> {
    return this.api.put<RepasseEntrada>(`/repasses/${id}`, dados);
  }

  excluirRepasse(id: number): Observable<void> {
    return this.api.delete<void>(`/repasses/${id}`);
  }

  // ---- agregados ----

  totais(de?: string, ate?: string): Observable<FinanceiroTotais> {
    return this.api.get<FinanceiroTotais>('/financeiro/totais', { de, ate });
  }

  pagamentos(f: {
    de?: string;
    ate?: string;
    ajudante_id?: number;
    origem?: string;
  }): Observable<Pagamento[]> {
    return this.api.get<Pagamento[]>('/financeiro/pagamentos', f);
  }
}
