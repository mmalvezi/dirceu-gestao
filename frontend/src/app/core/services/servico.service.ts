import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../api.service';
import { ExclusaoMaquina, Servico, ServicoDetalhe, ServicoEntrada } from '../models';
import { EntradaPayload } from './maquina.service';

export interface ServicoPayload {
  descricao?: string;
  cliente?: string | null;
  valor?: number;
  data_inicio?: string;
  data_finalizacao?: string | null;
  status?: string;
  obs?: string | null;
}

@Injectable({ providedIn: 'root' })
export class ServicoService {
  private api = inject(ApiService);

  listar(status?: string, q?: string): Observable<Servico[]> {
    return this.api.get<Servico[]>('/servicos', { status, q });
  }

  detalhe(id: number): Observable<ServicoDetalhe> {
    return this.api.get<ServicoDetalhe>(`/servicos/${id}`);
  }

  criar(dados: ServicoPayload): Observable<Servico> {
    return this.api.post<Servico>('/servicos', dados);
  }

  atualizar(id: number, dados: ServicoPayload): Observable<Servico> {
    return this.api.put<Servico>(`/servicos/${id}`, dados);
  }

  excluir(id: number): Observable<ExclusaoMaquina> {
    return this.api.delete<ExclusaoMaquina>(`/servicos/${id}`);
  }

  criarEntrada(servicoId: number, dados: EntradaPayload): Observable<ServicoEntrada> {
    return this.api.post<ServicoEntrada>(`/servicos/${servicoId}/diario`, dados);
  }

  atualizarEntrada(
    servicoId: number,
    entradaId: number,
    dados: EntradaPayload,
  ): Observable<ServicoEntrada> {
    return this.api.put<ServicoEntrada>(`/servicos/${servicoId}/diario/${entradaId}`, dados);
  }

  excluirEntrada(servicoId: number, entradaId: number): Observable<void> {
    return this.api.delete<void>(`/servicos/${servicoId}/diario/${entradaId}`);
  }

  pdf(id: number): Observable<Blob> {
    return this.api.getBlob(`/pdf/servico/${id}`);
  }
}
