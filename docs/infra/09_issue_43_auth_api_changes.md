# Issue #43 변경사항 정리

작성일: 2026-03-18  
브랜치: `auth-api`

## 1. 대상 이슈

upstream issue:

- `#43` `[backend] 사용자 인증 API — 이메일 회원가입 / 로그인 / JWT`

요구 범위:

- `POST /auth/login`
- `POST /auth/logout`
- `DELETE /auth/withdraw`
- `POST /auth/token/refresh`
- JWT 미들웨어
- HTTPS 강제 리다이렉트 설정

아키텍처 메모:

- 페이지 인증은 Django Session 기반
- JWT는 FastAPI ↔ Django 내부 연동용 유지

## 2. 이번 변경의 핵심

현재 코드 기준으로 `#43` 범위에 맞춰 아래를 반영했다.

- 이메일 로그인 후 JWT Access/Refresh 발급 API 추가
- 로그아웃 시 refresh token blacklist 처리 추가
- 회원 탈퇴 API 추가
- 회원가입 API를 실제 동작하도록 수정
- SimpleJWT blacklist 활성화
- HTTPS 관련 보안 설정을 환경변수 기반으로 추가

## 3. 수정 파일

- [settings.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/config/settings.py)
- [.env.example](/home/playdata/SKN22-Final-2Team-WEB/infra/.env.example)
- [auth_urls.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/auth_urls.py)
- [views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/views.py)
- [tests.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/tests.py)

## 4. 추가/정리된 엔드포인트

현재 `api/auth` 아래 인증 API는 아래와 같다.

- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `DELETE /api/auth/withdraw/`
- `POST /api/auth/token/refresh/`

참고:

- 경로명은 이슈 설명의 `/auth/...`를 현재 프로젝트 네임스페이스에 맞춰 `/api/auth/...` 형태로 적용했다

## 5. 엔드포인트 상세

### 5.1 POST /api/auth/login/

역할:

- 이메일/비밀번호 로그인
- JWT Access/Refresh 발급

요청 예시:

```json
{
  "email": "auth@example.com",
  "password": "Password123!"
}
```

성공 응답 예시:

```json
{
  "access": "<jwt-access>",
  "refresh": "<jwt-refresh>",
  "user": {
    "id": 1,
    "email": "auth@example.com",
    "nickname": "Auth User",
    "profile_image_url": null
  }
}
```

실패:

- 이메일/비밀번호 누락 시 `400`
- 인증 실패 시 `401`

### 5.2 POST /api/auth/logout/

역할:

- refresh token blacklist 처리
- Django 세션도 함께 로그아웃

요청 예시:

```json
{
  "refresh": "<jwt-refresh>"
}
```

성공 응답:

- `204 No Content`

실패:

- refresh 누락 시 `400`
- 잘못된 refresh token 시 `400`

### 5.3 DELETE /api/auth/withdraw/

역할:

- 현재 로그인한 사용자 탈퇴
- 전달된 refresh token이 있으면 blacklist 처리
- 세션 로그아웃 처리

요청 예시:

```json
{
  "refresh": "<jwt-refresh>"
}
```

성공 응답:

- `204 No Content`

실패:

- 보호된 주문 데이터 등으로 삭제 불가 시 `409`
- 잘못된 refresh token 시 `400`

### 5.4 POST /api/auth/token/refresh/

역할:

- 기존 SimpleJWT refresh 갱신 엔드포인트 유지

현재 위치:

- [urls.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/config/urls.py)

## 6. 회원가입 API 보완

기존 `RegisterView`는 `TODO` 상태였다.

이번에 실제 동작하도록 수정했다.

현재:

- 이메일/비밀번호 기반 사용자 생성
- `UserProfile` 자동 생성
- 회원가입 직후 JWT Access/Refresh 발급

경로:

- `POST /api/users/register/`

## 7. JWT/보안 설정 변경

[settings.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/config/settings.py) 변경점:

- `rest_framework_simplejwt.token_blacklist` 추가
- `BLACKLIST_AFTER_ROTATION = True`

추가된 보안 환경변수:

- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SESSION_COOKIE_SECURE`
- `DJANGO_CSRF_COOKIE_SECURE`

샘플 위치:

- [.env.example](/home/playdata/SKN22-Final-2Team-WEB/infra/.env.example)

현재 기본값:

- 모두 `False`

의미:

- 로컬 개발에서는 HTTP 테스트 가능
- 운영 환경에서는 `True`로 전환 가능

## 8. 구현상 주의점

### 8.1 페이지 인증과 API 인증은 분리됨

현재 프로젝트는 혼합 구조다.

- MVT 웹 페이지: Django Session 인증
- REST API: JWT 인증

즉, 이번 `#43`의 JWT API는 주로 API 소비자(FastAPI 내부 연동 포함) 기준이다.

### 8.2 로그아웃은 refresh token이 필요함

현재 `logout`은 refresh token blacklist를 전제로 한다.

즉, 단순 access token만으로는 충분하지 않다.

### 8.3 회원 탈퇴는 보호된 주문 데이터가 있으면 막힘

[orders/models.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/orders/models.py) 에서 일부 관계는 `RESTRICT`다.

따라서 사용자 삭제가 항상 가능한 구조는 아니고, 이런 경우 `409`를 반환하도록 처리했다.

## 9. 테스트 추가

[tests.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/tests.py)에 아래 테스트를 추가했다.

- `test_login_returns_access_and_refresh_tokens`
- `test_logout_blacklists_refresh_token`
- `test_withdraw_deletes_user`

기존 소셜 로그인 테스트 3건과 합쳐 총 6건이다.

## 10. 검증 결과

실행한 검증:

- `python manage.py check`
- `docker compose build django`
- `docker compose run --rm django python manage.py test users`

결과:

- Django system check 통과
- `users` 테스트 총 6건 통과

## 11. 현재 남은 것

`#43` 요구와 비교했을 때 현재 남은 검토 포인트:

- 운영 환경에서 HTTPS 강제 리다이렉트 실제 적용 여부
- MVT 로그인/로그아웃 흐름과 JWT API 역할 구분 문서화
- 필요 시 token rotation 정책 세부 조정

## 12. 요약

이번 변경으로 `#43`의 핵심 인증 API는 현재 프로젝트 구조에 맞는 형태로 구현됐다.

- 이메일 로그인 → JWT 발급
- 로그아웃 → refresh blacklist
- 회원 탈퇴 → 사용자 삭제 + 세션 종료
- refresh 갱신 유지
- 보안 설정 환경변수화
