import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../core/auth.service';
import { Icon } from '../../core/icon';

@Component({
  selector: 'app-login',
  imports: [FormsModule, Icon],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private auth = inject(AuthService);
  private router = inject(Router);

  username = '';
  password = '';
  erro = signal('');
  carregando = signal(false);

  entrar(): void {
    if (!this.username || !this.password || this.carregando()) return;
    this.erro.set('');
    this.carregando.set(true);
    this.auth.login(this.username, this.password).subscribe({
      next: () => this.router.navigate(['/']),
      error: (e: HttpErrorResponse) => {
        this.carregando.set(false);
        this.erro.set(
          e.status === 401
            ? 'Usuário ou senha inválidos.'
            : 'Não foi possível conectar. O servidor está no ar?',
        );
      },
    });
  }
}
