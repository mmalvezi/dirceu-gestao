"""Configurações da aplicação (lidas do .env com defaults de desenvolvimento)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Banco de dados. Em dev é SQLite (arquivo local); em produção, PostgreSQL.
    DATABASE_URL: str = "sqlite:///./dirceu.db"

    # Segredo para assinar os tokens JWT. TROCAR em produção.
    SECRET_KEY: str = "dev-trocar-em-producao"

    # Validade do token de acesso, em minutos (default: 7 dias).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Credenciais do admin inicial (usadas no seed).
    ADMIN_USERNAME: str = "dirceu"
    ADMIN_PASSWORD: str = "trocar-senha"

    # Pasta onde as mídias (fotos/logo) são salvas.
    MEDIA_DIR: str = "./media"

    # Origens permitidas no CORS. "*" libera todas; aceita lista separada por vírgula.
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        """Converte CORS_ORIGINS em lista, tratando '*' e itens separados por vírgula."""
        raw = self.CORS_ORIGINS.strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
