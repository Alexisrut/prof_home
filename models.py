from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ContactInfo:
    user_id: int               # PK, also FK to User.user_id
    fio: str                   # ФИО
    kkr_name: str              # Имя ККР
    group_number: str          # Номер группы
    location: str              # Место проживания
    blocks: str                # Блоки (можно хранить как строку с разделителем)
    phone: str                 # Номер телефона
    vk: str                    # ВК
    tg: str                    # ТГ
    email: str                 # Почта
    budget: bool               # Бюджет (True) / платка (False)
    in_profcom: bool           # Состоит ли в профкоме


@dataclass
class User:
    user_id: int               # PK, FK to ContactInfo.user_id
    user_name: str             # ФИО (из ККР)
    kkr_score: int             # Баллы ККР
    group_number: str          # Номер группы
    blocks: str                # Блоки
    banned: bool               # БАН
    super_user: bool           # Права SuperUser (председатель)
    admin: bool                # Права Админа


@dataclass
class Guide:
    guide_id: int              # PK
    title: str                 # Название гайда
    owner_block: str           # Блок "owner"
    text: str                  # Текст
    original_link: Optional[str] = None  # Ссылка на оригинал




# ── Add to your existing User model / dataclass ───────────
# If your User is a dataclass:

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class User:
    user_id: int
    user_name: str
    hashed_password: str          # ← NEW FIELD
    kkr_score: int
    group_number: str
    blocks: str
    banned: bool = False
    super_user: bool = False
    admin: bool = False


# ── New tiny model for refresh tokens ─────────────────────
@dataclass
class RefreshToken:
    token: str
    user_id: int
    expires_at: datetime