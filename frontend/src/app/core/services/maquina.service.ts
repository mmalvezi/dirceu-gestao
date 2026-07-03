import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../api.service';
import { DiarioEntrada, Maquina, MaquinaDetalhe } from '../models';

export interface MaquinaPayload {
  nome?: string;
  cliente?: string;
  empreita?: number;
  data_inicio?: string;
  data_finalizacao?: string | null;
  status?: string;
  obs?: string | null;
}

export interface TrabalhoPayload {
  ajudante_id?: number | null;
  ajudante_nome?: string | null;
  horas: number;
  valor: number;
  origem: string;
}

export interface EntradaPayload {
  data: string;
  descricao: string;
  trabalhos: TrabalhoPayload[];
}

@Injectable({ providedIn: 'root' })
export class MaquinaService {
  private api = inject(ApiService);

  listar(status?: string, q?: string): Observable<Maquina[]> {
    return this.api.get<Maquina[]>('/maquinas', { status, q });
  }

  detalhe(id: number): Observable<MaquinaDetalhe> {
    return this.api.get<MaquinaDetalhe>(`/maquinas/${id}`);
  }

  criar(dados: MaquinaPayload): Observable<Maquina> {
    return this.api.post<Maquina>('/maquinas', dados);
  }

  atualizar(id: number, dados: MaquinaPayload): Observable<Maquina> {
    return this.api.put<Maquina>(`/maquinas/${id}`, dados);
  }

  excluir(id: number): Observable<void> {
    return this.api.delete<void>(`/maquinas/${id}`);
  }

  // ---- diário ----

  criarEntrada(maquinaId: number, dados: EntradaPayload): Observable<DiarioEntrada> {
    return this.api.post<DiarioEntrada>(`/maquinas/${maquinaId}/diario`, dados);
  }

  atualizarEntrada(
    maquinaId: number,
    entradaId: number,
    dados: EntradaPayload,
  ): Observable<DiarioEntrada> {
    return this.api.put<DiarioEntrada>(`/maquinas/${maquinaId}/diario/${entradaId}`, dados);
  }

  excluirEntrada(maquinaId: number, entradaId: number): Observable<void> {
    return this.api.delete<void>(`/maquinas/${maquinaId}/diario/${entradaId}`);
  }

  pdf(id: number): Observable<Blob> {
    return this.api.getBlob(`/pdf/maquina/${id}`);
  }
}
