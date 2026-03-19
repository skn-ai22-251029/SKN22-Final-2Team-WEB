# Auth API 변경사항 정리

작성일: 2026-03-18  
브랜치: `auth-api`

## 1. 작업 목적

기존 Django 백엔드는 다음 상태였다.

- JWT 발급 API는 `SimpleJWT` 기본 엔드포인트만 존재
- 회원가입 API는 `RegisterView` 스텁만 존재
- Google, Naver, Kakao 소셜 로그인 연동은 전혀 없음
- 사용자와 소셜 계정을 연결하는 별도 매핑 테이블도 없음

이번 작업의 목적은 다음 3개 provider에 대해 공통된 백엔드 인증 API를 만드는 것이었다.

- Google
- Naver
- Kakao

최종적으로 프론트는 OAuth provider에서 `authorization code`를 받은 뒤, Django API에 `code`를 전달하면 Django가:

1. provider access token 교환
2. provider 사용자 프로필 조회
3. 로컬 사용자 생성 또는 기존 사용자 연결
4. TailTalk JWT 발급

까지 처리하도록 구성했다.

## 2. 전체 흐름

구현된 인증 흐름은 아래와 같다.

1. 프론트가 `GET /api/auth/providers/?redirect_uri=...` 호출
2. Django가 provider별 로그인 URL과 `state`를 생성해서 반환
3. 사용자가 Google/Naver/Kakao 로그인 수행
4. 프론트 콜백 페이지가 `code`와 필요 시 `state`를 수신
5. 프론트가 `POST /api/auth/social/<provider>/` 호출
6. Django가 provider 토큰 교환 및 사용자 정보 조회
7. `SocialAccount`로 기존 계정 조회
8. 없으면 이메일 기준 기존 `User` 연결 또는 신규 생성
9. `RefreshToken.for_user()`로 JWT 발급
10. 프론트는 반환된 `access`, `refresh`를 사용

## 3. 변경 파일

### 수정된 파일

- [infra/.env.example](/home/playdata/SKN22-Final-2Team-WEB/infra/.env.example)
- [settings.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/config/settings.py)
- [urls.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/config/urls.py)
- [models.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/models.py)
- [views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/views.py)

### 새로 추가된 파일

- [auth_urls.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/auth_urls.py)
- [oauth.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/oauth.py)
- [tests.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/tests.py)
- [0002_socialaccount.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/migrations/0002_socialaccount.py)

## 4. 세부 변경사항

### 4.1 설정 추가

[settings.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/config/settings.py)에 `SOCIAL_AUTH_PROVIDERS` 설정을 추가했다.

provider별로 아래 항목을 관리한다.

- `client_id`
- `client_secret`
- `authorize_url`
- `token_url`
- `userinfo_url`

현재 등록된 provider:

- `google`
- `naver`
- `kakao`

이 설정을 기반으로 백엔드가 provider별 인가 URL 생성과 code 교환을 처리한다.

### 4.2 환경변수 추가

[infra/.env.example](/home/playdata/SKN22-Final-2Team-WEB/infra/.env.example)에 아래 항목을 추가했다.

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `KAKAO_CLIENT_ID`
- `KAKAO_CLIENT_SECRET`

실제 동작을 위해서는 `infra/.env` 또는 배포 환경에 값이 반드시 들어가야 한다.

### 4.3 SocialAccount 모델 추가

[models.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/models.py)에 `SocialAccount` 모델을 추가했다.

역할:

- 로컬 `User`와 provider 계정을 연결
- provider별 고유 사용자 ID 저장
- provider 응답 원본 일부를 `extra_data`로 보존

주요 필드:

- `user`
- `provider`
- `provider_user_id`
- `email`
- `extra_data`
- `created_at`
- `updated_at`

제약조건:

- `provider + provider_user_id` 조합 유니크

마이그레이션 파일은 [0002_socialaccount.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/migrations/0002_socialaccount.py)에 추가했다.

### 4.4 OAuth provider 클라이언트 추가

[oauth.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/oauth.py)를 새로 만들었다.

구성 요소:

- `SocialAuthError`
- `SocialUserProfile` dataclass
- `OAuthProviderClient`

`OAuthProviderClient` 책임:

- provider 설정 로드
- authorization URL 생성
- authorization code를 provider access token으로 교환
- userinfo API 호출
- provider별 응답을 공통 프로필 구조로 정규화

provider별 처리 차이:

- Google: `openid email profile` scope 사용
- Naver: token 교환 시 `state` 필수
- Kakao: `profile_nickname profile_image account_email` scope 사용

현재 구현은 Python 표준 라이브러리 `urllib.request`를 사용해서 외부 요청을 처리한다. 별도 HTTP 클라이언트 패키지는 추가하지 않았다.

### 4.5 신규 인증 API 추가

[auth_urls.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/auth_urls.py)를 추가하고, [urls.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/config/urls.py)에서 `/api/auth/` 하위로 연결했다.

추가된 엔드포인트:

- `GET /api/auth/providers/`
- `POST /api/auth/social/<provider>/`

#### GET /api/auth/providers/

목적:

- 프론트가 provider 목록과 로그인 URL을 한 번에 가져오기 위함

쿼리 파라미터:

- `redirect_uri` 선택

동작:

- 각 provider의 설정 여부 확인
- `redirect_uri`가 주어지고 provider가 configured 상태이면 authorization URL과 `state` 생성

응답 예시:

```json
{
  "providers": [
    {
      "provider": "google",
      "configured": true,
      "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
      "state": "random-state"
    },
    {
      "provider": "naver",
      "configured": true,
      "authorization_url": "https://nid.naver.com/oauth2.0/authorize?...",
      "state": "random-state"
    },
    {
      "provider": "kakao",
      "configured": true,
      "authorization_url": "https://kauth.kakao.com/oauth/authorize?...",
      "state": "random-state"
    }
  ]
}
```

#### POST /api/auth/social/<provider>/

목적:

- 프론트가 받은 OAuth `code`를 백엔드에 넘겨 로컬 JWT를 발급받기 위함

요청 바디:

```json
{
  "code": "oauth-code",
  "redirect_uri": "http://localhost:3000/auth/google/callback",
  "state": "optional-or-required-for-naver"
}
```

필수 값:

- `code`
- `redirect_uri`

추가 규칙:

- `naver`는 `state`가 필요

응답 예시:

```json
{
  "provider": "google",
  "access": "<jwt-access-token>",
  "refresh": "<jwt-refresh-token>",
  "is_new_user": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "nickname": "TailTalk User",
    "profile_image_url": "https://example.com/avatar.png"
  }
}
```

### 4.6 사용자 생성 및 연결 정책

[views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/views.py)의 `SocialLoginView`는 아래 정책으로 사용자 계정을 처리한다.

#### 1. 기존 소셜 계정 존재 시

- `SocialAccount(provider, provider_user_id)`로 조회
- 기존 `User` 반환
- 닉네임/프로필 이미지는 최신 provider 정보로 동기화

#### 2. 소셜 계정은 없지만 동일 이메일 사용자가 있는 경우

- 기존 `User`에 현재 provider를 연결
- `UserProfile`이 없으면 생성
- 프로필 정보 동기화

#### 3. 둘 다 없을 경우

- 새 `User` 생성
- 새 `UserProfile` 생성
- 새 `SocialAccount` 생성

#### 이메일이 없는 provider 응답 처리

- fallback 이메일 형식 사용
- 형식: `<provider>_<provider_user_id>@oauth.local`

이 방식으로 이메일이 응답되지 않는 경우에도 Django `User.email` 유니크 제약을 유지한다.

## 5. 테스트 추가

[tests.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/tests.py)에 3개 테스트를 추가했다.

### test_social_login_creates_user_and_tokens

- 새 소셜 사용자 로그인 시
- `User`, `UserProfile`, `SocialAccount` 생성 확인
- `access`, `refresh` 토큰 발급 확인

### test_social_login_links_existing_user_by_email

- 동일 이메일의 기존 로컬 사용자가 있을 때
- 새 유저를 만들지 않고 provider 연결
- 프로필 동기화 반영 확인

### test_provider_list_returns_authorization_urls_for_configured_providers

- provider 목록 API 호출 시
- 3개 provider와 authorization URL, `state` 반환 확인

## 6. 검증 결과

실행한 검증:

- `python manage.py check`
- `python -m compileall services/django/users services/django/config`
- `docker compose run --rm django python manage.py test users`

결과:

- Django system check 통과
- Python 문법 컴파일 통과
- `users` 테스트 3건 통과

참고:

- 호스트 환경에서 직접 `manage.py test`는 Postgres 연결 문제로 실패했고
- Docker 컨테이너 내부 테스트는 정상 통과했다

## 7. 프론트 연동 시 필요한 사항

프론트에서 최소한 다음 흐름이 필요하다.

1. 로그인 페이지 진입
2. `GET /api/auth/providers/?redirect_uri=...` 호출
3. 사용자가 provider 버튼 클릭
4. 반환된 `authorization_url`로 이동
5. 콜백 페이지에서 `code`, `state` 수신
6. `POST /api/auth/social/<provider>/` 호출
7. 응답의 `access`, `refresh` 저장

콜백 페이지 예시:

- `/auth/google/callback`
- `/auth/naver/callback`
- `/auth/kakao/callback`

주의:

- `redirect_uri`는 provider 개발자 콘솔에 등록된 값과 정확히 일치해야 한다
- Naver는 `state`를 반드시 프론트에서 저장 후 다시 전달해야 한다

## 8. 현재 남아 있는 작업

이번 작업은 백엔드 auth API까지 구현한 상태다. 실제 서비스 완성을 위해서는 아래가 남아 있다.

- 프론트 로그인 UI/콜백 페이지 구현
- 토큰 저장 전략 확정
- 로그아웃 처리 정책 확정
- refresh 토큰 재발급 흐름 프론트 연결
- provider 개발자 콘솔 redirect URI 등록
- 실제 운영용 `.env` 값 입력
- 필요 시 소셜 가입 직후 추가 프로필 입력 플로우 설계

## 9. 주의사항

- 아직 `RegisterView` 자체는 `TODO` 상태다
- 소셜 로그인은 정상 추가됐지만 일반 이메일 회원가입/로그인 UX는 별도 구현이 필요하다
- provider 응답 스키마가 변경되면 [oauth.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/oauth.py) 정규화 로직 수정이 필요하다
- 현재는 provider access token 자체를 저장하지 않는다
- 현재는 provider unlink, logout, re-consent 같은 후속 기능은 구현하지 않았다
