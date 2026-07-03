import { Location } from '@angular/common';
import { Component, inject, input } from '@angular/core';
import { Router } from '@angular/router';

/** "← Voltar" padrão das telas que não são raiz: history.back() com fallback. */
@Component({
  selector: 'app-voltar',
  template: `
    <button class="back" type="button" (click)="voltar()"
            style="padding:8px 4px;min-height:40px">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
           width="16" height="16"><path d="M15 5l-7 7 7 7"/></svg>
      {{ rotulo() }}
    </button>
  `,
})
export class Voltar {
  rotulo = input('Voltar');
  fallback = input('/');

  private location = inject(Location);
  private router = inject(Router);

  voltar(): void {
    if (window.history.length > 1) {
      this.location.back();
    } else {
      this.router.navigate([this.fallback()]);
    }
  }
}
