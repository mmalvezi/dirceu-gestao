import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../api.service';
import { Fechamento, FechamentoDetalhe, FechamentoPrevia } from '../models';

@Injectable({ providedIn: 'root' })
export class FechamentoService {
  private api = inject(ApiService);

  previa(de: string, ate: string): Observable<FechamentoPrevia> {
    return this.api.get<FechamentoPrevia>('/fechamentos/previa', { de, ate });
  }

  registrar(dados: {
    periodo_de: string;
    periodo_ate: string;
    obs?: string | null;
  }): Observable<FechamentoDetalhe> {
    return this.api.post<FechamentoDetalhe>('/fechamentos', dados);
  }

  listar(): Observable<Fechamento[]> {
    return this.api.get<Fechamento[]>('/fechamentos');
  }

  detalhe(id: number): Observable<FechamentoDetalhe> {
    return this.api.get<FechamentoDetalhe>(`/fechamentos/${id}`);
  }

  pdfFechamento(id: number): Observable<Blob> {
    return this.api.getBlob(`/pdf/fechamento/${id}`);
  }

  pdfPrevia(de: string, ate: string): Observable<Blob> {
    return this.api.getBlob('/pdf/fechamento-previa', { de, ate });
  }
}
