import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../api.service';
import { Dashboard } from '../models';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private api = inject(ApiService);

  get(de?: string, ate?: string): Observable<Dashboard> {
    return this.api.get<Dashboard>('/dashboard', { de, ate });
  }
}
