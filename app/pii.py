from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),
    "personal_name": re.compile(r"\b(?:ho ten|h\u1ecd t\u00ean|full name|customer name|ten khach hang|t\u00ean kh\u00e1ch h\u00e0ng)[:\s#-]*[^0-9\n,;]{2,80}", re.IGNORECASE),
    "student_id": re.compile(r"\b(?:mssv|ma sinh vien|m\u00e3 sinh vi\u00ean|student id)[:\s#-]*[A-Z0-9]{6,12}\b", re.IGNORECASE),
    "phone_vn": re.compile(r"(?:\+84|0)[ \.-]?\d{3}[ \.-]?\d{3}[ \.-]?\d{3,4}"), # Matches 090 123 4567, 090.123.4567, etc.
    "cccd": re.compile(r"\b\d{12}\b"),
    "cmnd": re.compile(r"\b(?:cmnd|cmt|chung minh nhan dan|ch\u1ee9ng minh nh\u00e2n d\u00e2n)[:\s#-]*\d{9}\b", re.IGNORECASE),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    "passport": re.compile(r"\b(?:passport|ho chieu|h\u1ed9 chi\u1ebfu|so ho chieu|s\u1ed1 h\u1ed9 chi\u1ebfu)[:\s#-]*[A-Z]\d{7,8}\b", re.IGNORECASE),
    "tax_code_vn": re.compile(r"\b(?:mst|ma so thue|m\u00e3 s\u1ed1 thu\u1ebf|tax code)[:\s#-]*\d{10}(?:-\d{3})?\b", re.IGNORECASE),
    "bank_account_vn": re.compile(r"\b(?:stk|so tai khoan|s\u1ed1 t\u00e0i kho\u1ea3n|bank account|account number)[:\s#-]*(?:\d[ -]?){8,16}\b", re.IGNORECASE),
    "social_insurance_vn": re.compile(r"\b(?:bhxh|bao hiem xa hoi|b\u1ea3o hi\u1ec3m x\u00e3 h\u1ed9i)[:\s#-]*\d{10}\b", re.IGNORECASE),
    "health_insurance_vn": re.compile(r"\b(?:bhyt|bao hiem y te|b\u1ea3o hi\u1ec3m y t\u1ebf)[:\s#-]*[A-Z]{2}\d{13}\b", re.IGNORECASE),
    "driver_license_vn": re.compile(r"\b(?:gplx|bang lai|b\u1eb1ng l\u00e1i|driver license)[:\s#-]*\d{10,12}\b", re.IGNORECASE),
    "license_plate_vn": re.compile(r"\b\d{2}[A-Z]\d?[- ]?\d{3,5}(?:\.\d{2})?\b", re.IGNORECASE),
    "date_of_birth": re.compile(r"\b(?:dob|date of birth|ngay sinh|ng\u00e0y sinh)[:\s#-]*(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.](?:19|20)\d{2}\b", re.IGNORECASE),
    "ip_address": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    "address_vn": re.compile(r"\b(?:address|dia chi|\u0111\u1ecba ch\u1ec9|noi o|n\u01a1i \u1edf|thuong tru|th\u01b0\u1eddng tr\u00fa|tam tru|t\u1ea1m tr\u00fa|phuong|ph\u01b0\u1eddng|quan|qu\u1eadn|huyen|huy\u1ec7n|tinh|t\u1ec9nh|thanh pho|th\u00e0nh ph\u1ed1|tp\.?)\b[:\s,.-]*[^\n;]{0,120}", re.IGNORECASE),
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = pattern.sub(f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
