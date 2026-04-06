from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
    user_id: int
    user_name: str
    hashed_password: str
    kkr_score: int
    group_number: str
    blocks: str
    banned: bool = False
    super_user: bool = False
    admin: bool = False


@dataclass
class Guide:
    guide_id: int              # PK
    title: str                 # Название гайда
    owner_block: str           # Блок "owner"
    text: str                  # Текст
    original_link: Optional[str] = None  # Ссылка на оригинал
