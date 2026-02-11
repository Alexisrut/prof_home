from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from .database import db
from .models import ContactInfo, User, Guide


app = FastAPI(title="Profcom backend")


# --- Auth / permissions (simplified) ---

class AuthUser(BaseModel):
    user_id: int


def get_current_user(user_id: int) -> User:
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_admin(cur: User = Depends(get_current_user)) -> User:
    if not cur.admin and not cur.super_user:
        raise HTTPException(status_code=403, detail="Admin rights required")
    return cur


def require_superuser(cur: User = Depends(get_current_user)) -> User:
    if not cur.super_user:
        raise HTTPException(status_code=403, detail="SuperUser rights required")
    return cur


# --- Schemas ---

class ContactInfoIn(BaseModel):
    fio: str
    kkr_name: str
    group_number: str
    location: str
    blocks: str
    phone: str
    vk: str
    tg: str
    email: EmailStr
    budget: bool
    in_profcom: bool


class UserIn(BaseModel):
    user_name: str
    kkr_score: int
    group_number: str
    blocks: str
    banned: bool = False
    super_user: bool = False
    admin: bool = False


class UserOut(BaseModel):
    user_id: int
    user_name: str
    kkr_score: int
    group_number: str
    blocks: str
    banned: bool
    super_user: bool
    admin: bool


class ContactInfoOut(ContactInfoIn):
    user_id: int


class GuideIn(BaseModel):
    title: str
    owner_block: str
    text: str
    original_link: Optional[str] = None


class GuideOut(GuideIn):
    guide_id: int


# --- Registration / login ---

@app.post("/register", response_model=UserOut)
def register(contact: ContactInfoIn, user_in: UserIn):
    """POST: registration – create contact_info + user."""
    contact_model = ContactInfo(
        user_id=0,
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
    user_model = User(
        user_id=0,
        user_name=user_in.user_name,
        kkr_score=user_in.kkr_score,
        group_number=user_in.group_number,
        blocks=user_in.blocks,
        banned=user_in.banned,
        super_user=user_in.super_user,
        admin=user_in.admin,
    )
    created = db.create_user_with_contact(contact_model, user_model)
    return UserOut(**created.__dict__)


@app.get("/login", response_model=UserOut)
def login(user_name: str):
    """GET: login by name, returns user info."""
    user = db.get_user_by_name(user_name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(**user.__dict__)


# --- Profile page ---

@app.get("/profile/{user_id}", response_model=UserOut)
def get_profile(user_id: int):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(**user.__dict__)


class ProfileUpdate(BaseModel):
    # fields that can be updated in both user and contact_info
    fio: Optional[str] = None
    kkr_name: Optional[str] = None
    group_number: Optional[str] = None
    location: Optional[str] = None
    blocks: Optional[str] = None
    phone: Optional[str] = None
    vk: Optional[str] = None
    tg: Optional[str] = None
    email: Optional[EmailStr] = None
    budget: Optional[bool] = None
    in_profcom: Optional[bool] = None


@app.patch("/profile/{user_id}", response_model=UserOut)
def update_profile(
    user_id: int,
    payload: ProfileUpdate,
    cur: User = Depends(get_current_user),
):
    """
    UPDATE contact_info/user – allowed for the user themself or any admin.
    """
    target = db.get_user(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if cur.user_id != user_id and not (cur.admin or cur.super_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    # update contact info
    db.update_contact(
        user_id,
        fio=payload.fio,
        kkr_name=payload.kkr_name,
        group_number=payload.group_number,
        location=payload.location,
        blocks=payload.blocks,
        phone=payload.phone,
        vk=payload.vk,
        tg=payload.tg,
        email=payload.email,
        budget=payload.budget,
        in_profcom=payload.in_profcom,
    )
    # sync some fields to user entity
    db.update_user(
        user_id,
        group_number=payload.group_number,
        blocks=payload.blocks,
    )
    updated = db.get_user(user_id)
    return UserOut(**updated.__dict__)


@app.delete("/profile/{user_id}")
def delete_user(
    user_id: int,
    cur: User = Depends(require_superuser),
):
    """DELETE user – only SuperUser."""
    if not db.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    db.delete_user(user_id)
    return {"status": "deleted"}


# --- Guides page ---

@app.get("/guides", response_model=List[GuideOut])
def list_guides():
    guides = db.list_guides()
    return [GuideOut(**g.__dict__) for g in guides]


@app.post("/guides", response_model=GuideOut)
def create_or_edit_guide(
    guide: GuideIn,
    cur: User = Depends(require_admin),
):
    g = Guide(
        guide_id=0,
        title=guide.title,
        owner_block=guide.owner_block,
        text=guide.text,
        original_link=guide.original_link,
    )
    created = db.create_guide(g)
    return GuideOut(**created.__dict__)


# --- Contact info page ---

@app.get("/contacts", response_model=List[ContactInfoOut])
def get_all_contacts():
    contacts = db.list_contacts()
    return [ContactInfoOut(**c.__dict__) for c in contacts]


class ContactFilter(BaseModel):
    group_number: Optional[str] = None
    blocks: Optional[str] = None
    in_profcom: Optional[bool] = None
    budget: Optional[bool] = None


@app.post("/contacts/filter", response_model=List[ContactInfoOut])
def filter_contacts(
    filt: ContactFilter,
    cur: User = Depends(require_admin),
):
    crit = {
        "group_number": filt.group_number,
        "blocks": filt.blocks,
        "in_profcom": filt.in_profcom,
        "budget": filt.budget,
    }
    contacts = db.filter_contacts(**crit)
    return [ContactInfoOut(**c.__dict__) for c in contacts]



