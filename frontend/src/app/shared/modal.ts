import { Component, output } from '@angular/core';

/** Casca de modal do protótipo (.modal-bg/.modal): mobile desliza de baixo. */
@Component({
  selector: 'app-modal',
  template: `
    <div class="modal-bg" (click)="aoClicarFora($event)">
      <div class="modal"><ng-content /></div>
    </div>
  `,
})
export class Modal {
  fechado = output<void>();

  aoClicarFora(e: MouseEvent): void {
    if (e.target === e.currentTarget) this.fechado.emit();
  }
}
