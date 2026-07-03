# Frontend — Dirceu (Caldeiraria & Solda)

Angular standalone + SCSS. O protótipo aprovado (`../dirceu-prototipo.html`) é o contrato visual.

## Rodando em desenvolvimento

Pré-requisito: backend rodando na porta 8002 (ver `../backend/README.md`).

```powershell
cd frontend
npm install
ng serve --port 4210
```

Abrir http://localhost:4210 — login: usuário `dirceu` (senha do seed/.env do backend).

> A porta **4210** evita conflito com outros projetos (`ng serve` padrão usa 4200).

## Estrutura

- `src/environments/environment.ts` — `apiUrl` (dev: `http://127.0.0.1:8002`)
- `src/styles.scss` — tokens e classes globais copiados do protótipo (seção 3 do plano)
- `src/app/core/` — models, formatação pt-BR, ApiService, AuthService, interceptor, guard, layout
- `src/app/features/` — telas (login + páginas)
