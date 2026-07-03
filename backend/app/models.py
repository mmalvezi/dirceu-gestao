"""Modelos SQLAlchemy 2.0 (seção 4 do plano mestre).

Só tipos genéricos (String, Integer, Numeric, Date, DateTime, Boolean, Text)
para funcionar tanto em SQLite (dev) quanto em PostgreSQL (prod).
Status/origem/tipo são String com valores controlados na aplicação (sem Enum de banco).
Dinheiro: Numeric(10, 2). Horas: Numeric(5, 1).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Config(Base):
    __tablename__ = "config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome_exibicao: Mapped[str] = mapped_column(
        String, default="Dirceu — Caldeiraria & Solda"
    )
    telefone: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    prox_fec: Mapped[int] = mapped_column(Integer, default=1)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)


class Ajudante(Base):
    __tablename__ = "ajudantes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    telefone: Mapped[str | None] = mapped_column(String, nullable=True)
    valor_hora_padrao: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    obs: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Maquina(Base):
    __tablename__ = "maquinas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    cliente: Mapped[str] = mapped_column(String)  # texto livre, sem cadastro
    empreita: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String, default="andamento")  # andamento/finalizada/fechada
    data_inicio: Mapped[date] = mapped_column(Date)
    data_finalizacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    obs: Mapped[str | None] = mapped_column(Text, nullable=True)
    fechamento_id: Mapped[int | None] = mapped_column(
        ForeignKey("fechamentos.id", ondelete="SET NULL"), nullable=True
    )

    diario: Mapped[list["DiarioEntrada"]] = relationship(
        back_populates="maquina",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_maquinas_status", "status"),)


class DiarioEntrada(Base):
    __tablename__ = "diario_entradas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    maquina_id: Mapped[int] = mapped_column(
        ForeignKey("maquinas.id", ondelete="CASCADE")
    )
    data: Mapped[date] = mapped_column(Date)
    descricao: Mapped[str] = mapped_column(Text)

    maquina: Mapped["Maquina"] = relationship(back_populates="diario")
    trabalhos: Mapped[list["DiarioTrabalho"]] = relationship(
        back_populates="entrada",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_diario_entradas_maquina_id_data", "maquina_id", "data"),)


class DiarioTrabalho(Base):
    __tablename__ = "diario_trabalhos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entrada_id: Mapped[int] = mapped_column(
        ForeignKey("diario_entradas.id", ondelete="CASCADE")
    )
    ajudante_id: Mapped[int | None] = mapped_column(
        ForeignKey("ajudantes.id", ondelete="SET NULL"), nullable=True
    )
    ajudante_nome: Mapped[str] = mapped_column(String)  # snapshot
    horas: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    origem: Mapped[str] = mapped_column(String)  # repasse/epr_direto/bolso

    entrada: Mapped["DiarioEntrada"] = relationship(back_populates="trabalhos")


class Recebimento(Base):
    __tablename__ = "recebimentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String)  # adiantamento/fechamento
    data: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    maquina_id: Mapped[int | None] = mapped_column(
        ForeignKey("maquinas.id", ondelete="SET NULL"), nullable=True
    )
    maquina_nome: Mapped[str | None] = mapped_column(String, nullable=True)  # snapshot
    status: Mapped[str] = mapped_column(String, default="aberto")  # aberto/quitado
    fechamento_id: Mapped[int | None] = mapped_column(
        ForeignKey("fechamentos.id", ondelete="SET NULL"), nullable=True
    )
    obs: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_recebimentos_tipo_status", "tipo", "status"),)


class RepasseEntrada(Base):
    __tablename__ = "repasse_entradas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    obs: Mapped[str | None] = mapped_column(Text, nullable=True)


class Fechamento(Base):
    __tablename__ = "fechamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String, unique=True)  # "FEC-0001"
    data_geracao: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    periodo_de: Mapped[date] = mapped_column(Date)
    periodo_ate: Mapped[date] = mapped_column(Date)
    total_devido: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total_adiantado: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    saldo: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    obs: Mapped[str | None] = mapped_column(Text, nullable=True)
