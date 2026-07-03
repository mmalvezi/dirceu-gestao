import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

import { ApiService } from './api.service';
import { Token } from './models';

const TOKEN_KEY = 'dirceu_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private api = inject(ApiService);
  private router = inject(Router);

  login(username: string, password: string): Observable<Token> {
    return this.api
      .postForm<Token>('/auth/login', { username, password })
      .pipe(tap((t) => localStorage.setItem(TOKEN_KEY, t.access_token)));
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.router.navigate(['/login']);
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }
}
