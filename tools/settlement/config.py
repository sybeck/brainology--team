import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BrandCredential:
    admin_id: str
    password: str


BRAND_KEY_MAP = {
    "부담제로": "BUDAMZERO",
    "브레인올로지": "BRAINOLOGY",
}


def get_brand_credential(brand: str) -> BrandCredential:
    """브랜드별 Cafe24 로그인 정보를 환경변수에서 읽어옴.
    CAFE24_{BRAND}_ADMIN_ID / CAFE24_{BRAND}_PASSWORD 우선,
    없으면 CAFE24_ADMIN_ID / CAFE24_PASSWORD 사용.
    """
    key = BRAND_KEY_MAP.get(brand, brand.upper().replace("-", "_").replace(" ", "_"))
    admin_id = os.getenv(f"CAFE24_{key}_ADMIN_ID") or os.getenv("CAFE24_ADMIN_ID", "")
    password = os.getenv(f"CAFE24_{key}_PASSWORD") or os.getenv("CAFE24_PASSWORD", "")
    return BrandCredential(admin_id=admin_id, password=password)


def get_download_dir() -> str:
    return os.getenv("CAFE24_DOWNLOAD_DIR", "teams/settlement/downloads")


def get_headless() -> bool:
    return os.getenv("CAFE24_HEADLESS", "true").lower() in ("true", "1", "yes")
