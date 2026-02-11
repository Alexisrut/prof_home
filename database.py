from __future__ import annotations

from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from models import User as UserDC, ContactInfo as ContactInfoDC, Guide as GuideDC


DATABASE_URL = "sqlite:///./profcom.db"

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


class UserORM(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String, nullable=False)
    kkr_score = Column(Integer, nullable=False)
    group_number = Column(String, nullable=False)
    blocks = Column(String, nullable=False)
    banned = Column(Boolean, default=False, nullable=False)
    super_user = Column(Boolean, default=False, nullable=False)
    admin = Column(Boolean, default=False, nullable=False)

    contact = relationship("ContactInfoORM", back_populates="user", uselist=False)


class ContactInfoORM(Base):
    __tablename__ = "contact_info"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    fio = Column(String, nullable=False)
    kkr_name = Column(String, nullable=False)
    group_number = Column(String, nullable=False)
    location = Column(String, nullable=False)
    blocks = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    vk = Column(String, nullable=False)
    tg = Column(String, nullable=False)
    email = Column(String, nullable=False)
    budget = Column(Boolean, nullable=False)
    in_profcom = Column(Boolean, nullable=False)

    user = relationship("UserORM", back_populates="contact")


class GuideORM(Base):
    __tablename__ = "guides"

    guide_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    owner_block = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    original_link = Column(String, nullable=True)


Base.metadata.create_all(bind=engine)


def _user_orm_to_dc(u: UserORM) -> UserDC:
    return UserDC(
        user_id=u.user_id,
        user_name=u.user_name,
        kkr_score=u.kkr_score,
        group_number=u.group_number,
        blocks=u.blocks,
        banned=u.banned,
        super_user=u.super_user,
        admin=u.admin,
    )


def _contact_orm_to_dc(c: ContactInfoORM) -> ContactInfoDC:
    return ContactInfoDC(
        user_id=c.user_id,
        fio=c.fio,
        kkr_name=c.kkr_name,
        group_number=c.group_number,
        location=c.location,
        blocks=c.blocks,
        phone=c.phone,
        vk=c.vk,
        tg=c.tg,
        email=c.email,
        budget=c.budget,
        in_profcom=c.in_profcom,
    )


def _guide_orm_to_dc(g: GuideORM) -> GuideDC:
    return GuideDC(
        guide_id=g.guide_id,
        title=g.title,
        owner_block=g.owner_block,
        text=g.text,
        original_link=g.original_link,
    )


class DB:
    """SQLAlchemy-backed database layer."""

    def __init__(self) -> None:
        self._SessionLocal = SessionLocal

    def _session(self) -> Session:
        return self._SessionLocal()

    # --- Users & ContactInfo ---

    def create_user_with_contact(
        self,
        contact: ContactInfoDC,
        user: UserDC,
    ) -> UserDC:
        with self._session() as session:
            u = UserORM(
                user_name=user.user_name,
                kkr_score=user.kkr_score,
                group_number=user.group_number,
                blocks=user.blocks,
                banned=user.banned,
                super_user=user.super_user,
                admin=user.admin,
            )
            session.add(u)
            session.flush()  # assign user_id

            c = ContactInfoORM(
                user_id=u.user_id,
                fio=contact.fio,
                kkr_name=contact.kkr_name,
                group_number=contact.group_number,
                location=contact.location,
                blocks=contact.blocks,
                phone=contact.phone,
                vk=contact.vk,
                tg=contact.tg,
                email=contact.email,
                budget=contact.budget,
                in_profcom=contact.in_profcom,
            )
            session.add(c)
            session.commit()
            session.refresh(u)

            return _user_orm_to_dc(u)

    def get_user(self, user_id: int) -> Optional[UserDC]:
        with self._session() as session:
            u = session.get(UserORM, user_id)
            if not u:
                return None
            return _user_orm_to_dc(u)

    def get_user_by_name(self, user_name: str) -> Optional[UserDC]:
        with self._session() as session:
            u = (
                session.query(UserORM)
                .filter(UserORM.user_name == user_name)
                .first()
            )
            if not u:
                return None
            return _user_orm_to_dc(u)

    def delete_user(self, user_id: int) -> None:
        with self._session() as session:
            u = session.get(UserORM, user_id)
            if u:
                session.delete(u)
            c = session.get(ContactInfoORM, user_id)
            if c:
                session.delete(c)
            session.commit()

    def update_user(self, user_id: int, **fields) -> Optional[UserDC]:
        with self._session() as session:
            u = session.get(UserORM, user_id)
            if not u:
                return None
            for k, v in fields.items():
                if v is None:
                    continue
                elif hasattr(u, k):
                    setattr(u, k, v)
            session.commit()
            session.refresh(u)
            return _user_orm_to_dc(u)

    def update_contact(self, user_id: int, **fields) -> Optional[ContactInfoDC]:
        with self._session() as session:
            c = session.get(ContactInfoORM, user_id)
            if not c:
                return None
            for k, v in fields.items():
                if v is None:
                    continue
                if hasattr(c, k):
                    setattr(c, k, v)
            session.commit()
            session.refresh(c)
            return _contact_orm_to_dc(c)

    def list_contacts(self) -> List[ContactInfoDC]:
        with self._session() as session:
            rows = session.query(ContactInfoORM).all()
            return [_contact_orm_to_dc(c) for c in rows]

    def filter_contacts(self, **criteria) -> List[ContactInfoDC]:
        with self._session() as session:
            q = session.query(ContactInfoORM)
            if criteria.get("group_number") is not None:
                q = q.filter(ContactInfoORM.group_number == criteria["group_number"])
            if criteria.get("blocks") is not None:
                q = q.filter(ContactInfoORM.blocks == criteria["blocks"])
            if criteria.get("in_profcom") is not None:
                q = q.filter(ContactInfoORM.in_profcom == criteria["in_profcom"])
            if criteria.get("budget") is not None:
                q = q.filter(ContactInfoORM.budget == criteria["budget"])
            rows = q.all()
            return [_contact_orm_to_dc(c) for c in rows]

    # --- Guides ---

    def list_guides(self) -> List[GuideDC]:
        with self._session() as session:
            rows = session.query(GuideORM).all()
            return [_guide_orm_to_dc(g) for g in rows]

    def create_guide(self, guide: GuideDC) -> GuideDC:
        with self._session() as session:
            g = GuideORM(
                title=guide.title,
                owner_block=guide.owner_block,
                text=guide.text,
                original_link=guide.original_link,
            )
            session.add(g)
            session.commit()
            session.refresh(g)
            return _guide_orm_to_dc(g)

    def update_guide(self, guide_id: int, **fields) -> Optional[GuideDC]:
        with self._session() as session:
            g = session.get(GuideORM, guide_id)
            if not g:
                return None
            for k, v in fields.items():
                if v is None:
                    continue
                if hasattr(g, k):
                    setattr(g, k, v)
            session.commit()
            session.refresh(g)
            return _guide_orm_to_dc(g)


# global singleton for now
db = DB()


