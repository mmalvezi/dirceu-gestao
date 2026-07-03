# Backend — Dirceu (Caldeiraria & Solda)

Backend FastAPI do sistema de gestão do Dirceu. **Fase 1:** fundação (config, database, `/health`).

## Requisitos

- Python 3.14
- Windows (comandos abaixo para PowerShell)

## Rodando em desenvolvimento

```powershell
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar dependências
pip install -r requirements.txt

# 3. (Opcional) copiar o .env.example e ajustar
copy .env.example .env

# 4. Rodar o servidor (porta 8002)
uvicorn app.main:app --reload --port 8002
```

## Conferir

- Health check: http://127.0.0.1:8002/health → `{"status":"ok","app":"dirceu-gestao"}`
- Documentação (Swagger): http://127.0.0.1:8002/docs
- A pasta `media/` é criada automaticamente na inicialização.

## Configuração

As variáveis de ambiente estão documentadas em [.env.example](.env.example). Sem um `.env`,
os defaults de desenvolvimento são usados (SQLite local, CORS liberado, etc.).
