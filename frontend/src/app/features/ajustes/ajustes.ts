import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth.service';
import { Icon } from '../../core/icon';
import { Config, Usuario } from '../../core/models';
import { ConfigService } from '../../core/services/config.service';

/** Ajustes: identidade (nome/telefone/logo), sessão e sobre. */
@Component({
  selector: 'app-ajustes',
  imports: [FormsModule, Icon],
  templateUrl: './ajustes.html',
})
export class AjustesPage implements OnInit {
  private svc = inject(ConfigService);
  private auth = inject(AuthService);

  config = signal<Config | null>(null);
  usuario = signal<Usuario | null>(null);
  salvo = signal(false);
  erro = signal('');
  enviandoLogo = signal(false);

  nome = '';
  telefone = '';

  ngOnInit(): void {
    this.svc.get().subscribe((c) => {
      this.config.set(c);
      this.nome = c.nome_exibicao;
      this.telefone = c.telefone ?? '';
    });
    this.svc.me().subscribe((u) => this.usuario.set(u));
  }

  logoUrl(): string | null {
    const c = this.config();
    return c?.logo_url ? environment.apiUrl + c.logo_url : null;
  }

  salvar(): void {
    this.erro.set('');
    if (!this.nome.trim()) {
      this.erro.set('O nome de exibição não pode ficar vazio.');
      return;
    }
    this.svc
      .atualizar({ nome_exibicao: this.nome.trim(), telefone: this.telefone.trim() || null })
      .subscribe({
        next: (c) => {
          this.config.set(c);
          this.salvo.set(true);
          setTimeout(() => this.salvo.set(false), 1600);
        },
        error: () => this.erro.set('Não foi possível salvar.'),
      });
  }

  aoEscolherLogo(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const arquivo = input.files?.[0];
    if (!arquivo) return;
    this.erro.set('');
    this.enviandoLogo.set(true);
    this.svc.enviarLogo(arquivo).subscribe({
      next: (c) => {
        this.config.set(c);
        this.enviandoLogo.set(false);
        input.value = '';
      },
      error: (e) => {
        this.enviandoLogo.set(false);
        input.value = '';
        const d = e?.error?.detail;
        this.erro.set(typeof d === 'string' ? d : 'Não foi possível enviar a imagem.');
      },
    });
  }

  removerLogo(): void {
    if (!confirm('Remover o logo?')) return;
    this.svc.removerLogo().subscribe((c) => this.config.set(c));
  }

  sair(): void {
    this.auth.logout();
  }
}
