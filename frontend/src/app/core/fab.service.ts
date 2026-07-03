import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

/** Canal do FAB "Lançar dia": o layout emite, a tela de máquinas reage. */
@Injectable({ providedIn: 'root' })
export class FabService {
  readonly cliques = new Subject<void>();
}
