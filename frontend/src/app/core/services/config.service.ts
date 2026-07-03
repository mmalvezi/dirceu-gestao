import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../api.service';
import { Config, Usuario } from '../models';

@Injectable({ providedIn: 'root' })
export class ConfigService {
  private api = inject(ApiService);

  get(): Observable<Config> {
    return this.api.get<Config>('/config');
  }

  atualizar(dados: { nome_exibicao?: string; telefone?: string | null }): Observable<Config> {
    return this.api.put<Config>('/config', dados);
  }

  enviarLogo(arquivo: File): Observable<Config> {
    const form = new FormData();
    form.append('file', arquivo);
    return this.api.postForm<Config>('/config/logo', form);
  }

  removerLogo(): Observable<Config> {
    return this.api.delete<Config>('/config/logo');
  }

  me(): Observable<Usuario> {
    return this.api.get<Usuario>('/auth/me');
  }
}
