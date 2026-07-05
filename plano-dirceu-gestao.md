# Plano Mestre — Sistema Dirceu (Caldeiraria & Solda)

> **Como usar este documento:** este é o plano de referência do projeto. O desenvolvimento é feito em FASES, uma de cada vez, com o Claude Code. Cada fase tem objetivo, entregas e critério de "pronto". Ao concluir uma fase, TESTAR antes de ir pra próxima. Este arquivo deve ficar na raiz do projeto (`plano-dirceu-gestao.md`) para o Claude Code consultar.

---

## 1. Visão geral

Sistema de gestão para o **Dirceu**, prestador PJ de caldeiraria e solda que gerencia projetos ("máquinas") dentro da EPR. Usuário único (login só do Dirceu). Protótipo visual já aprovado pelo cliente (`dirceu-prototipo.html` — é a referência de layout e comportamento).

**O coração do sistema é a MÁQUINA (projeto/empreita)** com seu **diário de obra**. Cada lançamento de diário alimenta, de uma vez: custos da máquina, financeiro (pagamentos a ajudantes com origem do dinheiro), dashboard e relatórios.

### Conceitos de negócio (IMPORTANTES — não simplificar)

- **Máquina/empreita**: ex. "Jato E120 — Metalúrgica Santa Fé", valor da empreita R$ 6.500. Status: `andamento` → `finalizada` (aguardando fechamento) → `fechada` (acertada e recebida).
- **Diário de obra**: por máquina, lançamentos por DIA: descrição do que foi feito + lista de quem trabalhou (ajudante, horas, valor pago, origem do pagamento).
- **Origem do pagamento a ajudante (3 tipos — chave do sistema):**
  - `repasse` — "Repasse EPR": a EPR manda dinheiro pro Dirceu repassar aos ajudantes. Não é custo do Dirceu, mas passa pela mão dele (precisa de prestação de contas).
  - `epr_direto` — "EPR direto": a EPR paga o ajudante diretamente, não passa pela mão do Dirceu.
  - `bolso` — "Do bolso": o Dirceu paga com dinheiro próprio. Entra no acerto dele com a EPR.
- **Caixa de repasse**: (verbas de repasse recebidas da EPR) − (pagamentos com origem `repasse`). Mostra quanto sobra/falta na mão do Dirceu.
- **Recebimentos do Dirceu**: `adiantamento` (recebe antes de terminar; fica **em aberto** até ser abatido) e `fechamento` (o acerto).
- **Fechamento por período**: escolhe De/Até → entram as máquinas **finalizadas** no período (empreita integral) − adiantamentos **em aberto** vinculados → **SALDO A RECEBER**. Ao "registrar o acerto": máquinas viram `fechada`, adiantamentos viram `quitado`, e nasce um recebimento tipo `fechamento` com o valor do saldo. Sem data fixa — adiantamentos ficam em aberto por quanto tempo for preciso.

---

## 2. Stack e decisões técnicas (aprendizados do projeto Everton — SEGUIR)

| Item | Decisão |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 + Alembic |
| Banco | SQLite em dev (arquivo `dirceu.db`, zero config) / PostgreSQL em produção (Docker). Usar só tipos genéricos nos modelos |
| Auth | JWT com **bcrypt direto (SEM passlib** — conflito com bcrypt 4.x) |
| PDF | **fpdf2** (100% Python, roda no Windows; NÃO usar WeasyPrint). Sanitizar texto pra latin-1 (função `L()`) |
| Frontend | Angular standalone + SCSS, PWA |
| Fotos/logo | Pillow reduz e salva em disco (`MEDIA_DIR`); caminho no banco |
| requirements.txt | **SEM pinos de versão** (Python local é 3.14; várias libs sem wheel pinada) |
| Porta backend dev | **8002** (8000 = EPR, 8001 = Everton) |
| Porta frontend dev | `ng serve --port 4210` (evita conflito com outros projetos) |
| Organização | Uma pasta do projeto com `backend/` e `frontend/` separados |
| Snapshot | Documentos/lançamentos gravam NOME (ajudante_nome, maquina_nome) além do FK — histórico não muda se cadastro mudar |
| Numeração | `FEC-0001` para fechamentos (contador `prox_fec` na tabela config) |
| Produção | Mesmo VPS do Everton. Compose próprio (db/api/web) SEM porta publicada no host; o **Caddy existente** roteia o domínio novo pro `web` deste projeto |

---

## 3. Identidade visual (extraída do protótipo aprovado — usar exatamente)

**Fontes:** Barlow Semi Condensed (display/títulos/números grandes), Barlow (corpo), monospace (valores).

**Tokens (styles.scss `:root`):**
```
--bg:#eef1f3; --card:#ffffff; --iron:#1c242c; --iron-2:#242e38;
--ink:#161c22; --slate:#5a6672; --slate-2:#8b95a0; --line:#dde3e8; --surf2:#f4f6f8;
--weld:#e05a00; --weld-d:#b84a02; --weld-soft:#fdeee2;      /* laranja solda = cor de ação */
--in:#178f52; --in-soft:#e3f4ea;                             /* entradas/positivo */
--pass:#2f6bb0; --pass-soft:#e7eff8;                         /* repasse/EPR (azul) */
--pocket:#c23a2e; --pocket-soft:#fbe9e7;                     /* do bolso (vermelho) */
--warn:#b7791f; --warn-soft:#fdf3e0;                         /* atenção/adiantamento */
--r:12px;
```

**Elementos marcantes do protótipo (replicar):** marca "DC" quadrada com losango laranja no canto; motivo visual de losango (quadrado rotacionado 45°) nos chips e na timeline do diário; sidebar escura (`--iron`) no desktop com indicador lateral laranja / tab bar escura no mobile; FAB laranja "Lançar dia" nas telas de máquinas; chips de origem coloridos (repasse/EPR=azul, bolso=vermelho); barras de margem (verde <45%, laranja 45–70%, vermelho >70% da empreita consumida); caixa escura para totais (SALDO A RECEBER); régua do fechamento (adiantado âmbar × saldo verde); rodapé "Malvezi Sistemas".

---

## 4. Modelo de dados

**config** — id, nome_exibicao ("Dirceu — Caldeiraria & Solda"), telefone, logo_filename (null), prox_fec (int, default 1)

**users** — id, username (único), hashed_password

**ajudantes** — id, nome, telefone (opc), valor_hora_padrao (num, opc — pré-preenche o lançamento), obs (opc), ativo (bool, default true)

**maquinas** — id, nome, cliente (TEXTO livre — sem cadastro de cliente, simplicidade), empreita (num), status (`andamento`/`finalizada`/`fechada`), data_inicio (date), data_finalizacao (date, null), obs (opc), fechamento_id (FK null → fechamentos, SET NULL)
  - **Exclusão:** máquina NÃO fechada pode ser excluída mesmo com lançamentos (com confirmação). O diário some (CASCADE); recebimentos e despesas vinculados são DESVINCULADOS (maquina_id→NULL, mantém maquina_nome — dinheiro/custo reais não somem). Máquina `fechada` (ou com recebimento `quitado`) → bloqueada: faz parte de um acerto registrado.

**diario_entradas** — id, maquina_id (FK CASCADE), data (date), descricao (texto)

**diario_trabalhos** — id, entrada_id (FK CASCADE), ajudante_id (FK SET NULL), ajudante_nome (snapshot), horas (num), valor (num), origem (`repasse`/`epr_direto`/`bolso`/`proprio`), proprio (bool, default false — "eu trabalhei": horas do Dirceu, valor 0, remuneração é a empreita; conta nas horas, não nos custos/pagamentos)

**despesas** — id, data (date), valor (num), categoria (`deslocamento`/`alimentacao`/`material`/`outros`), descricao (opc), maquina_id (FK SET NULL, opc), maquina_nome (snapshot, opc) — gastos do próprio Dirceu; entram no "resultado do período"

**recebimentos** — id, tipo (`adiantamento`/`fechamento`), data (date), valor (num), maquina_id (FK SET NULL, opc), maquina_nome (snapshot, opc), status (`aberto`/`quitado` — só relevante p/ adiantamento; fechamento nasce `quitado`), fechamento_id (FK null, SET NULL), obs (opc)

**repasse_entradas** — id, data (date), valor (num), obs (opc) — verbas que a EPR mandou pro Dirceu repassar

**fechamentos** — id, numero (único, "FEC-0001"), data_geracao, periodo_de, periodo_ate, total_devido (num), total_adiantado (num), saldo (num), obs (opc)

**Derivados (nunca colunas) — contabilidade do DIRCEU:** custo_dirceu da máquina = Σ trabalhos origem `bolso` + Σ despesas vinculadas (repasse/EPR direto são pagos pela EPR — visíveis como custo_epr, FORA da margem); margem = empreita − custo_dirceu; pct_consumido = custo_dirceu/empreita; horas = Σ TODAS as horas (inclusive `proprio` — esforço, não dinheiro); caixa de repasse = Σ repasse_entradas − Σ trabalhos origem `repasse`; saído do bolso = Σ trabalhos origem `bolso`.

---

## 5. Contrato da API (prefixos)

- `POST /auth/login`, `GET /auth/me`
- `GET/PUT /config`, `POST/DELETE /config/logo`
- `GET/POST/PUT/DELETE /ajudantes` (lista com filtro `ativo`, e `?q=`)
- `GET/POST/PUT/DELETE /maquinas` (lista com `?status=&q=`; GET /{id} traz diário completo + custos/horas/margem calculados)
- `POST/PUT/DELETE /maquinas/{id}/diario` (entrada com lista de trabalhos aninhada; PUT substitui os trabalhos da entrada)
- `GET/POST/PUT/DELETE /recebimentos` (filtros `?tipo=&status=&de=&ate=`)
- `GET/POST/PUT/DELETE /repasses` (verbas de repasse)
- `GET/POST/PUT/DELETE /despesas` (filtros `?de=&ate=&categoria=&maquina_id=`)
- `GET /financeiro/pagamentos?de=&ate=[&ajudante_id=][&origem=]` (lista "pagos a ajudantes"; exclui trabalhos próprios)
- `GET /financeiro/totais?de=&ate=` (origens + caixa de repasse + adiantado aberto + despesas_periodo)
- `GET /financeiro/resultado?de=&ate=` (ganho real: recebimentos − bolso − despesas)
- `GET /fechamentos/previa?de=&ate=` (calcula sem gravar: máquinas finalizadas no período + adiantamentos abertos vinculados + saldo)
- `POST /fechamentos` (registra o acerto: efetiva status/quitações, gera número, cria recebimento tipo fechamento) · `GET /fechamentos` (histórico)
- `GET /dashboard` (KPIs, horas por dia da semana, margens, avisos, texto do resumo WhatsApp)
- PDFs: `GET /pdf/maquina/{id}`, `GET /pdf/periodo?de=&ate=`, `GET /pdf/ajudantes?de=&ate=[&ajudante_id=]`, `GET /pdf/entradas?de=&ate=`, `GET /pdf/resultado?de=&ate=` (ganho real do período), `GET /pdf/fechamento/{id}` (e `GET /pdf/fechamento-previa?de=&ate=`)

---

## 6. Fases de desenvolvimento

### FASE 1 — Fundação do backend
Projeto FastAPI em `backend/`: `app/main.py` (CORS, `/health`, StaticFiles em `/media`), `app/config.py` (settings via .env: DATABASE_URL com default sqlite `dirceu.db`, SECRET_KEY, ADMIN_*, MEDIA_DIR), `app/database.py`, `.env.example`, requirements sem pinos.
**Pronto quando:** `uvicorn app.main:app --port 8002` responde `/health`.

### FASE 2 — Modelos + migração + seed
Todos os modelos da seção 4, Alembic configurado, migração inicial, seed (linha config + admin `dirceu`).
**Pronto quando:** `alembic upgrade head` cria o banco; seed roda no startup.

### FASE 3 — Autenticação JWT
`security.py` (hash/verify com bcrypt direto, create_access_token, get_current_user), `routers/auth.py`. Todas as rotas seguintes protegidas.
**Pronto quando:** login devolve token; rota protegida sem token = 401.

### FASE 4 — Config/branding + mídia
GET/PUT /config; upload/remoção de logo (Pillow reduz, salva em MEDIA_DIR).
**Pronto quando:** logo sobe, aparece em /media/..., PUT altera nome/telefone.

### FASE 5 — Ajudantes + Máquinas (CRUD)
CRUDs com filtros; máquina lista com custo/horas/margem calculados e badge de status; snapshot de nada ainda (só cadastros).
**Pronto quando:** cria/edita/inativa ajudante; cria máquina com empreita; lista traz números calculados (zerados).

### FASE 6 — Diário de obra (núcleo do sistema)
Lançamento de dia: data, descrição, N trabalhos (ajudante_id + snapshot do nome, horas, valor, origem). Editar/excluir entrada. GET da máquina devolve diário ordenado por data desc + totais atualizados.
**Pronto quando:** lançar um dia com 2 ajudantes atualiza custo/horas/margem da máquina; editar/excluir reflete.

### FASE 7 — Financeiro
Recebimentos (adiantamento nasce `aberto`; CRUD com filtros por tipo/status/período) + repasse_entradas (CRUD). Endpoint auxiliar de totais do financeiro (caixa de repasse, saído do bolso no período, pago pela EPR direto, custo total).
**Pronto quando:** registra adiantamento vinculado a máquina; totais de origem batem com o diário lançado.

### FASE 8 — Fechamento
`/fechamentos/previa` (De/Até → máquinas finalizadas no período, empreita integral; adiantamentos ABERTOS vinculados a essas máquinas OU sem vínculo, a abater; saldo). `POST /fechamentos` efetiva: numero FEC-XXXX, máquinas → `fechada` + fechamento_id, adiantamentos → `quitado` + fechamento_id, cria recebimento tipo `fechamento` (valor = saldo, status quitado). Histórico.
**Pronto quando:** cenário completo funciona — finaliza máquina, tem adiantamento aberto, prévia mostra saldo certo, registrar acerto efetiva tudo e o adiantamento some dos "abertos".

### FASE 9 — Dashboard + resumo WhatsApp
`GET /dashboard`: KPIs da semana (horas, pago a ajudantes com split repasse/bolso/epr_direto, adiantado em aberto, a receber de finalizadas), horas por dia (seg–dom), margem das máquinas em andamento (com % consumido), AVISOS por regra: (a) máquina finalizada há N dias sem fechamento (citar adiantamento a abater se houver); (b) custo ≥ 60% da empreita em andamento (≥70% = vermelho); (c) caixa de repasse com sobra/falta; (d) adiantamento aberto há mais de 30 dias. Campo `resumo_whatsapp` (texto pronto, formato do protótipo).
**Pronto quando:** números batem com os lançamentos de teste; avisos aparecem/somem conforme os dados.

### FASE 10 — Relatórios PDF (fpdf2)
Identidade: cabeçalho escuro `--iron` com marca/losango laranja, rótulos em laranja-escuro, valores em mono, chips de origem, caixa escura de total, rodapé fino. Sanitização `L()` em tudo. Os 5 relatórios da seção 5 + PDF da prévia de fechamento. Filtros por querystring.
**Pronto quando:** os 5 PDFs abrem corretos com dados reais de teste e refletem filtros.

### FASE 11 — Fundação do frontend Angular
Projeto standalone em `frontend/` (porta dev 4210), `environment.ts` apiUrl `http://127.0.0.1:8002`, styles.scss com tokens/fontes da seção 3, core (ApiService com getBlob/postForm, AuthService, guard, interceptor), tela de login (marca DC), layout sidebar/tabbar + FAB global "Lançar dia" (visível nas telas de máquinas), formato de moeda/data (`formatDate` SEM `new Date()` em string YYYY-MM-DD — evita bug de fuso).
**Pronto quando:** login funciona, navegação troca telas vazias, visual bate com o protótipo.

### FASE 12a — Telas: Máquinas + detalhe + diário
Lista de máquinas (cards com barra de margem, badge de status, últimos lançamentos), criar/editar máquina (modal), detalhe com os 4 números + barra + diário (timeline de losango), modal "Lançar dia" (data, descrição, N ajudantes com horas/valor/origem — origem como select de 3 opções com chip colorido; botão + ajudante), editar/excluir entrada. Botão "Finalizar máquina" (status → finalizada).
**Pronto quando:** fluxo completo de lançar/editar dia funciona no celular e desktop; números atualizam ao vivo.

### FASE 12b — Telas: Financeiro + Fechamento
Financeiro com 3 abas (segmented): Recebimentos (lista com chip aberto/quitado, + Adiantamento), Pagos a ajudantes (lista derivada do diário com chip de origem), Acerto & origens (os 6 KPIs do protótipo + registrar verba de repasse). Fechamento: De/Até, prévia (lista devido × abatimentos, régua visual, caixa SALDO A RECEBER), botões Gerar PDF e Registrar acerto (com confirmação), histórico de fechamentos.
**Pronto quando:** cenário do backend (fase 8) todo operável pela tela.

### FASE 12c — Telas: Início (dashboard) + Relatórios + Ajustes
Início: KPIs, avisos, gráfico de horas por dia (barras CSS), margens em andamento, card Resumo WhatsApp com botão Copiar. Relatórios: os 5 cards com filtros (período; máquina; ajudante quando aplicável) baixando PDF via getBlob. Ajustes: nome/telefone/logo.
**Pronto quando:** dashboard reflete os dados; todos os PDFs baixam pela tela.

### FASE 13 — PWA + ícone
`@angular/pwa`; manifest ("Dirceu — Caldeiraria & Solda", short_name "Dirceu", background `#eef1f3`, theme `#1c242c`); ícone personalizado (marca DC com losango laranja — gerar conjunto: 72–512, maskable 192/512, apple-touch, favicons); excluir `/api/**` do cache do service worker.
**Pronto quando:** DevTools > Application > Manifest mostra os ícones; instala no celular (após HTTPS).

### FASE 14 — Deploy (mesmo VPS do Everton)
- `backend/Dockerfile` + `docker-entrypoint.sh` (espera banco → alembic upgrade → uvicorn :8000, LF!), `frontend/Dockerfile` multi-stage (node build → nginx:alpine) + `nginx.conf` (proxy `^~ /api/` → api:8000 com barra final; try_files SPA; client_max_body_size 20M), `environment.production.ts` (apiUrl `/api`), `docker-compose.yml` (db postgres:16-alpine + volumes `db_data`/`media_data`; api; web **SEM ports** — rede interna), `.env.example` de produção, `DEPLOY.md`.
- **Integração com o Caddy existente:** os dois composes precisam se enxergar. Caminho recomendado: rede Docker externa compartilhada (ex.: `caddy_net`) — declarar no compose do Dirceu (`networks: [caddy_net]`, external) e garantir que o Caddy e o `web` do Dirceu estejam nela; no `Caddyfile` do Everton, adicionar bloco do domínio do Dirceu → `reverse_proxy dirceu-web:80` (usar container_name fixo, ex. `dirceu-web`) e `docker exec caddy caddy reload` (ou `docker compose restart caddy`).
- Servidor: `git clone` do repo do Dirceu, `.env` (senhas SÓ letras e números — `@` quebra a DATABASE_URL!), `docker compose up -d --build` (build do Angular: um projeto por vez; swap de 2GB já existe).
- DNS: registro A do domínio do Dirceu → IP do VPS. HTTPS automático pelo Caddy.
**Pronto quando:** `https://dominio-do-dirceu` abre com cadeado, login funciona, Everton continua no ar intacto.

---

## 7. Regras de ouro (não negociar)

1. Uma fase por vez; testar antes de avançar.
2. Nunca colar segredos (senhas/tokens) em chats ou no repositório; `.env` só no servidor.
3. Senhas de banco: só letras e números.
4. Em produção, NUNCA `docker compose down -v` (apaga dados). Atualização = `git pull` + `docker compose up -d --build`.
5. Snapshot de nomes em lançamentos e documentos.
6. Datas: strings `YYYY-MM-DD` no front, sem `new Date('...')` direto (fuso).
7. PDFs: todo texto passa pela sanitização latin-1.
8. Mobile-first no diário: lançar um dia tem que ser rápido no celular (é o uso nº 1 do Dirceu).
