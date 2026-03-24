import re

from .models import UserProfile

MIN_NICKNAME_LENGTH = 2
MAX_NICKNAME_LENGTH = 12
FALLBACK_NICKNAME = "user"
NICKNAME_PATTERN = re.compile(r"^[가-힣A-Za-z0-9]{2,12}$")
NICKNAME_SANITIZE_PATTERN = re.compile(r"[^가-힣A-Za-z0-9]")
NICKNAME_POLICY_MESSAGE = "닉네임은 한글, 영문, 숫자만 2~12자까지 사용할 수 있습니다."
NICKNAME_DUPLICATE_MESSAGE = "이미 사용 중인 닉네임입니다."
NICKNAME_REQUIRED_MESSAGE = "닉네임을 입력해 주세요."


def sanitize_nickname_seed(seed):
    if seed is None:
        return ""
    return NICKNAME_SANITIZE_PATTERN.sub("", str(seed)).strip()


def normalize_nickname_seed(seed, fallback_seed=None):
    candidate = sanitize_nickname_seed(seed)
    fallback = sanitize_nickname_seed(fallback_seed)

    if len(candidate) < MIN_NICKNAME_LENGTH:
        candidate = fallback
    if len(candidate) < MIN_NICKNAME_LENGTH:
        candidate = FALLBACK_NICKNAME

    return candidate[:MAX_NICKNAME_LENGTH]


def is_nickname_available(nickname, exclude_user=None):
    queryset = UserProfile.objects.filter(nickname=nickname)
    exclude_user_id = getattr(exclude_user, "pk", exclude_user)
    if exclude_user_id is not None:
        queryset = queryset.exclude(user_id=exclude_user_id)
    return not queryset.exists()


def get_nickname_policy_error(nickname):
    nickname = (nickname or "").strip()
    if not nickname:
        return NICKNAME_REQUIRED_MESSAGE
    if not NICKNAME_PATTERN.fullmatch(nickname):
        return NICKNAME_POLICY_MESSAGE
    return None


def get_nickname_duplicate_error(nickname, exclude_user=None):
    if not is_nickname_available(nickname, exclude_user=exclude_user):
        return NICKNAME_DUPLICATE_MESSAGE
    return None


def get_nickname_validation_error(nickname, exclude_user=None):
    return get_nickname_policy_error(nickname) or get_nickname_duplicate_error(nickname, exclude_user=exclude_user)


def build_unique_nickname(seed, fallback_seed=None, exclude_user=None):
    base = normalize_nickname_seed(seed, fallback_seed=fallback_seed)
    candidate = base
    suffix = 2

    while not is_nickname_available(candidate, exclude_user=exclude_user):
        suffix_text = str(suffix)
        truncated_base = base[: max(1, MAX_NICKNAME_LENGTH - len(suffix_text))]
        candidate = f"{truncated_base}{suffix_text}"
        suffix += 1

    return candidate
