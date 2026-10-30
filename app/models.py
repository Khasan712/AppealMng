import enum
from datetime import datetime
from sqlalchemy import String, Enum, ForeignKey, DateTime, BigInteger, func, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserRole(str, enum.Enum):
    APPEALER = "APPEALER"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class AppealStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class AppealSource(str, enum.Enum):
    WEB = "WEB"
    TELEGRAM = "TELEGRAM"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(13), index=True, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(100))
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.APPEALER)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    categories: Mapped[list["Category"]] = relationship(back_populates="responsible_user")
    appeals: Mapped[list["Appeal"]] = relationship(back_populates="author", foreign_keys="Appeal.author_id")


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    responsible_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    responsible_user: Mapped[User] = relationship(User, foreign_keys=[responsible_user_id], back_populates="categories")
    appeals: Mapped[list["Appeal"]] = relationship(back_populates="category")


class Appeal(Base):
    __tablename__ = "appeals"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(13))
    description: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[AppealStatus] = mapped_column(Enum(AppealStatus, name="appeal_status"), default=AppealStatus.NEW, index=True)
    source: Mapped[AppealSource] = mapped_column(Enum(AppealSource, name="appeal_source"), default=AppealSource.WEB, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    category: Mapped[Category] = relationship(back_populates="appeals")
    author: Mapped[User] = relationship(back_populates="appeals", foreign_keys=[author_id])
    history: Mapped[list["AppealStatusHistory"]] = relationship(back_populates="appeal", order_by="AppealStatusHistory.created_at")


class AppealStatusHistory(Base):
    __tablename__ = "appeal_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id"), index=True)
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    new_status: Mapped[AppealStatus] = mapped_column(Enum(AppealStatus, name="appeal_status"))
    previous_status: Mapped[AppealStatus | None] = mapped_column(Enum(AppealStatus, name="appeal_status"), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    appeal: Mapped[Appeal] = relationship(back_populates="history")
    updated_by: Mapped[User] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id"))
    message: Mapped[str] = mapped_column(Text)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())





