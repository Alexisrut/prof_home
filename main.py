from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from database import db
from models import ContactInfo, User, Guide
import logging
# ── Import the NEW auth module instead of inline helpers ───
from auth import (
    hash_password,
    verify_password,
    create_token_pair,
    refresh_tokens,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_current_user,      # replaces old get_current_user
    require_admin,         # replaces old require_admin
    require_superuser,     # replaces old require_superuser
)


app = FastAPI(title="Profcom backend")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
# ═══════════════════════════════════════════════════════════
#  SCHEMAS
# ═══════════════════════════════════════════════════════════

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
    password: str                    # ← NEW: plain-text password from client
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


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginIn(BaseModel):
    user_name: str
    password: str


class ProfileUpdate(BaseModel):
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


class ContactFilter(BaseModel):
    group_number: Optional[str] = None
    blocks: Optional[str] = None
    in_profcom: Optional[bool] = None
    budget: Optional[bool] = None


# ═══════════════════════════════════════════════════════════
#  AUTH ENDPOINTS  (NEW)
# ═══════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=TokenPair, status_code=201)
def register(contact: ContactInfoIn, user_in: UserIn):
    """
    Register a new user.
    Body JSON:
    {
      "contact": { ... },
      "user_in": { "user_name": "...", "password": "...", ... }
    }
    Returns access + refresh tokens immediately.
    """
    logger.info(f"Arguments: {user_in.model_dump_json()}")
    # Check duplicate
    if db.get_user_by_name(user_name=user_in.user_name):
        raise HTTPException(409, "User name already taken")

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
        hashed_password=hash_password(user_in.password),   # ← hash!
        kkr_score=user_in.kkr_score,
        group_number=user_in.group_number,
        blocks=user_in.blocks,
        banned=user_in.banned,
        super_user=user_in.super_user,
        admin=user_in.admin,
    )
    created = db.create_user_with_contact(contact_model, user_model)

    # Return tokens so the user is logged-in right away
    return create_token_pair(created.user_id)


@app.post("/auth/login", response_model=TokenPair)
def login(body: LoginIn):
    """
    Authenticate with user_name + password → get tokens.
    """
    user = db.get_user_by_name(body.user_name)
    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    if user.banned:
        raise HTTPException(403, "User is banned")

    return create_token_pair(user.user_id)


@app.post("/auth/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest):
    """
    Exchange a refresh token for a new access + refresh pair.
    Old refresh token is deleted (rotation).
    """
    return refresh_tokens(body.refresh_token)


@app.post("/auth/logout")
def logout(
    body: RefreshRequest,
    cur: User = Depends(get_current_user),    # must be authenticated
):
    """Revoke a single refresh token (one device)."""
    revoke_refresh_token(body.refresh_token)
    return {"detail": "Logged out"}


@app.post("/auth/logout-all")
def logout_all(cur: User = Depends(get_current_user)):
    """Revoke ALL refresh tokens for the current user."""
    revoke_all_user_tokens(cur.user_id)
    return {"detail": "Logged out from all devices"}


# ═══════════════════════════════════════════════════════════
#  PROFILE   (protected by Bearer token now)
# ═══════════════════════════════════════════════════════════

@app.get("/profile/me", response_model=UserOut)
def my_profile(cur: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserOut(**cur.__dict__)


@app.get("/profile/{user_id}", response_model=UserOut)
def get_profile(user_id: int):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return UserOut(**user.__dict__)


@app.patch("/profile/{user_id}", response_model=UserOut)
def update_profile(
    user_id: int,
    payload: ProfileUpdate,
    cur: User = Depends(get_current_user),         # ← Bearer token now
):
    target = db.get_user(user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if cur.user_id != user_id and not (cur.admin or cur.super_user):
        raise HTTPException(403, "Forbidden")

    db.update_contact(
        user_id,
        fio=payload.fio, kkr_name=payload.kkr_name,
        group_number=payload.group_number, location=payload.location,
        blocks=payload.blocks, phone=payload.phone,
        vk=payload.vk, tg=payload.tg,
        email=payload.email, budget=payload.budget,
        in_profcom=payload.in_profcom,
    )
    db.update_user(user_id, group_number=payload.group_number, blocks=payload.blocks)
    updated = db.get_user(user_id)
    return UserOut(**updated.__dict__)


@app.delete("/profile/{user_id}")
def delete_user(user_id: int, cur: User = Depends(require_superuser)):
    if not db.get_user(user_id):
        raise HTTPException(404, "User not found")
    db.delete_user(user_id)
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════
#  GUIDES
# ═══════════════════════════════════════════════════════════

@app.get("/guides", response_model=List[GuideOut])
def list_guides():
    return [GuideOut(**g.__dict__) for g in db.list_guides()]


@app.post("/guides", response_model=GuideOut)
def create_guide(guide: GuideIn, cur: User = Depends(require_admin)):
    g = Guide(guide_id=0, title=guide.title, owner_block=guide.owner_block,
              text=guide.text, original_link=guide.original_link)
    created = db.create_guide(g)
    return GuideOut(**created.__dict__)


# ═══════════════════════════════════════════════════════════
#  CONTACTS
# ═══════════════════════════════════════════════════════════

@app.get("/contacts", response_model=List[ContactInfoOut])
def get_all_contacts():
    return [ContactInfoOut(**c.__dict__) for c in db.list_contacts()]


@app.post("/contacts/filter", response_model=List[ContactInfoOut])
def filter_contacts(filt: ContactFilter, cur: User = Depends(require_admin)):
    contacts = db.filter_contacts(
        group_number=filt.group_number, blocks=filt.blocks,
        in_profcom=filt.in_profcom, budget=filt.budget,
    )
    return [ContactInfoOut(**c.__dict__) for c in contacts]