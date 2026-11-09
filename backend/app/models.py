from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from .database import Base


# FinTrack currently stores one currency per installation. Two fractional digits
# are therefore the documented storage precision until currency support exists.
MONEY_PRECISION = 14
MONEY_SCALE = 2
MONEY_TYPE = Numeric(precision=MONEY_PRECISION, scale=MONEY_SCALE)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(254), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    amount = Column(MONEY_TYPE, nullable=False)
    type = Column(String(10), nullable=False)
    category = Column(String(80), nullable=False, default="Other")
    date = Column(Date, nullable=False)


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_budget_user_category"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(80), nullable=False)
    limit = Column(MONEY_TYPE, nullable=False)


class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    target_amount = Column(MONEY_TYPE, nullable=False)
    saved_amount = Column(MONEY_TYPE, nullable=False, default=0)
