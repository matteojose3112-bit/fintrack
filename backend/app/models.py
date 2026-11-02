from sqlalchemy import Column, Date, Float, Integer, String
from .database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(160), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(10), nullable=False)
    category = Column(String(80), nullable=False, default="Other")
    date = Column(Date, nullable=False)

class Budget(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(80), unique=True, nullable=False)
    limit = Column(Float, nullable=False)

class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    target_amount = Column(Float, nullable=False)
    saved_amount = Column(Float, nullable=False, default=0)
