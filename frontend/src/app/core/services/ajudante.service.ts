import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../api.service';
import { Ajudante } from '../models';

@Injectable({ providedIn: 'root' })
export class AjudanteService {
  private api = inject(ApiService);

  listar(ativo?: boolean, q?: string): Observable<Ajudante[]> {
    return this.api.get<Ajudante[]>('/ajudantes', { ativo, q });
  }

  criar(dados: {
    nome: string;
    telefone?: string | null;
    valor_hora_padrao?: number | null;
    obs?: string | null;
  }): Observable<Ajudante> {
    return this.api.post<Ajudante>('/ajudantes', dados);
  }
}
