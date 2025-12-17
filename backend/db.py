from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    create_engine,
    Integer,
    Float,
    String,
    DateTime,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from backend.config import DB_PATH, DATA_DIR


class Base(DeclarativeBase):
    pass


class Tick(Base):
    __tablename__ = "ticks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(30), index=True)
    price: Mapped[float] = mapped_column(Float)
    qty: Mapped[float] = mapped_column(Float)


Index("ix_ticks_symbol_ts", Tick.symbol, Tick.ts)


@dataclass
class DB:
    engine_url: str
    engine: any
    SessionLocal: any


def get_db() -> DB:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    engine_url = f"sqlite:///{DB_PATH}"
    engine = create_engine(engine_url, future=True)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return DB(engine_url=engine_url, engine=engine, SessionLocal=SessionLocal)


def init_db(db: DB) -> None:
    Base.metadata.create_all(bind=db.engine)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def insert_tick(
    db: DB,
    symbol: str,
    price: float,
    qty: float,
    ts: Optional[datetime] = None,
) -> None:
    if ts is None:
        ts = now_utc()
    with db.SessionLocal() as session:
        session.add(
            Tick(
                ts=ts,
                symbol=symbol.lower(),
                price=float(price),
                qty=float(qty),
            )
        )
        session.commit()


def fetch_recent_ticks(db: DB, symbol: str, limit: int = 200):
    with db.SessionLocal() as session:
        return (
            session.query(Tick)
            .filter(Tick.symbol == symbol.lower())
            .order_by(Tick.ts.desc())
            .limit(limit)
            .all()
        )
