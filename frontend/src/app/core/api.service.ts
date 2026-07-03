import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';

type Params = Record<string, string | number | boolean | null | undefined>;

/** Cliente HTTP tipado da API (base = environment.apiUrl). */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  private params(p?: Params): HttpParams {
    let hp = new HttpParams();
    if (p) {
      for (const [k, v] of Object.entries(p)) {
        if (v !== null && v !== undefined && v !== '') hp = hp.set(k, String(v));
      }
    }
    return hp;
  }

  get<T>(path: string, p?: Params): Observable<T> {
    return this.http.get<T>(this.base + path, { params: this.params(p) });
  }

  post<T>(path: string, body: unknown): Observable<T> {
    return this.http.post<T>(this.base + path, body);
  }

  put<T>(path: string, body: unknown): Observable<T> {
    return this.http.put<T>(this.base + path, body);
  }

  delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(this.base + path);
  }

  /** PDFs e outros binários. */
  getBlob(path: string, p?: Params): Observable<Blob> {
    return this.http.get(this.base + path, {
      params: this.params(p),
      responseType: 'blob',
    });
  }

  /** Form-encoded (login OAuth2) ou multipart (upload de arquivo). */
  postForm<T>(path: string, data: Record<string, string> | FormData): Observable<T> {
    if (data instanceof FormData) {
      return this.http.post<T>(this.base + path, data);
    }
    const body = new HttpParams({ fromObject: data });
    return this.http.post<T>(this.base + path, body.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  }
}
