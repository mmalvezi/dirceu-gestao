# Deploy — Dirceu (segundo stack no VPS do Everton)

O VPS já tem Docker, swap de 2 GB e o **Caddy** (stack do Everton) nas portas 80/443
com HTTPS automático. O Dirceu entra como um segundo compose **sem publicar portas**:
o Caddy roteia `dirceufernandes.com.br` → `dirceu-web:80` pela rede externa `caddy_net`.

## 1. DNS
Registro **A** de `dirceufernandes.com.br` → IP do VPS (o Caddy emite o HTTPS sozinho).

## 2. No servidor
```bash
git clone https://github.com/mmalvezi/dirceu-gestao.git
cd dirceu-gestao
cp .env.example .env && nano .env   # senhas SÓ letras/números; SECRET_KEY: openssl rand -hex 32
```

## 3. Rede compartilhada com o Caddy
```bash
docker network create caddy_net   # ignora o erro se já existir
```
No stack do **Everton** (ver o repo dele): garantir que o serviço do Caddy esteja
conectado à `caddy_net` (compose: `networks: [caddy_net]` + `external: true`) e
adicionar ao `Caddyfile`:
```
dirceufernandes.com.br {
    reverse_proxy dirceu-web:80
}
```
Recarregar: `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`
(ou `docker compose restart caddy` no stack do Everton).

## 4. Subir o Dirceu
```bash
docker compose up -d --build
```
> O build do Angular é pesado no VPS: rode **um build por vez** (não rebuilde o
> Everton em paralelo). O primeiro start aplica as migrações e cria o admin.

## 5. Verificar
```bash
docker compose ps                       # db (healthy), api, dirceu-web no ar
docker compose logs api | tail         # "[seed] usuário admin ..." no 1º start
docker exec dirceu-web wget -qO- http://api:8000/health   # {"status":"ok",...}
```
Abrir `https://dirceufernandes.com.br` (cadeado do Caddy) → login → lançar um dia.
No celular: instalar o PWA (menu do navegador → "Instalar app").

## 6. Atualizações
```bash
cd dirceu-gestao && git pull && docker compose up -d --build
```

## ⚠️ Regras de produção
- **NUNCA** rode `docker compose down -v` — o `-v` APAGA o banco e as fotos.
  Atualização é sempre `git pull` + `up -d --build`.
- Backup do banco: `docker compose exec db pg_dump -U dirceu dirceu > backup.sql`.
- O `.env` fica SÓ no servidor (está no .gitignore) — nunca em chat/repositório.

## Validação local (opcional, antes do servidor)
`docker compose config` valida o arquivo; a rede externa exige
`docker network create caddy_net` na máquina local só pra validação.
