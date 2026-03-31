# 운영 배포 전환 체크리스트

이 문서는 현재 테스트용 Elastic Beanstalk 배포 구성을 실제 운영 환경으로 전환할 때 바꿔야 하는 값과 확인 포인트를 정리한 문서다.

## 1. 공통 원칙

- 애플리케이션 런타임 값은 GitHub Actions가 배포용 `.env`를 만들 때 `GitHub Secrets`에서 읽는다.
- 같은 키를 `GitHub Secrets`와 EB 환경변수에 중복 등록하지 않는다.
- `WEB`는 EB 환경변수를 비워 두는 구성을 권장한다.
- `AI`는 private Docker 이미지 pull을 위해 `DOCKER_USERNAME`, `DOCKER_PASSWORD`만 EB 환경변수로 주입한다.

## 2. WEB 운영 전환 시 필수 값

### GitHub Secrets

다음 값은 `WEB` 저장소의 `Settings > Secrets and variables > Actions > Repository secrets`에 등록한다.

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
DJANGO_SECRET_KEY
INTERNAL_SERVICE_TOKEN
APP_BASE_URL
FASTAPI_INTERNAL_CHAT_URL
DJANGO_ALLOWED_HOSTS
CORS_ALLOWED_ORIGINS
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
KAKAO_CLIENT_ID
KAKAO_CLIENT_SECRET
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

### 값 형식

- `APP_BASE_URL`
  - 예: `https://app.example.com`
  - URL 전체를 넣는다.
- `FASTAPI_INTERNAL_CHAT_URL`
  - 예: `https://api.example.com/api/chat/`
  - URL 전체와 마지막 `/api/chat/`까지 포함한다.
- `DJANGO_ALLOWED_HOSTS`
  - 예: `app.example.com,www.app.example.com`
  - `http://` 또는 `https://`를 넣지 않는다.
  - `*.` 형식 대신 정확한 호스트를 콤마로 넣는 쪽을 권장한다.
- `CORS_ALLOWED_ORIGINS`
  - 예: `https://app.example.com,https://www.example.com`
  - `*`는 사용하지 않는다.

### 선택 값

- S3를 실제로 사용할 때만 아래 값을 추가한다.

```text
AWS_S3_BUCKET_NAME
AWS_S3_CUSTOM_DOMAIN
AWS_S3_ENDPOINT_URL
```

## 3. AI 운영 전환 시 필수 값

### GitHub Secrets

다음 값은 `AI` 저장소의 `Settings > Secrets and variables > Actions > Repository secrets`에 등록한다.

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
OPENAI_API_KEY
LANGSMITH_TRACING
LANGSMITH_API_KEY
LANGSMITH_PROJECT
LANGSMITH_ENDPOINT
LANGSMITH_WORKSPACE_ID
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

### EB 환경변수

`AI`는 private Docker 이미지를 받기 위해 아래 값만 EB 환경변수로 주입한다.

```text
DOCKER_USERNAME
DOCKER_PASSWORD
```

현재 workflow는 `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`을 기준으로 위 두 값을 자동 생성하도록 구성되어 있다.

## 4. 운영 도메인으로 바꿀 때 같이 수정할 부분

현재 workflow에는 테스트용 이름이 들어가 있으므로 운영 전환 시 함께 바꿔야 한다.

### WEB workflow

파일: `.github/workflows/ci-cd.yml`

- `DJANGO_IMAGE_REPO`
- `DJANGO_EB_APP_NAME`
- `DJANGO_EB_ENV_NAME`
- 배포 트리거 브랜치

### AI workflow

파일: `services/fastapi/.github/workflows/ci-cd.yml`

- `FASTAPI_IMAGE_REPO`
- `FASTAPI_EB_APP_NAME`
- `FASTAPI_EB_ENV_NAME`
- 배포 트리거 브랜치

운영에서는 `develop` 자동 배포 대신 `main`, `release`, 또는 승인 후 배포 흐름으로 분리하는 것을 권장한다.

## 5. HTTPS 운영 전환 체크리스트

현재 테스트 환경은 HTTP 중심 구성이므로, 운영에서 HTTPS를 사용할 경우 아래 작업이 필요하다.

1. ALB 또는 HTTPS 종료 지점을 준비한다.
2. ACM 인증서를 연결한다.
3. Nginx가 `X-Forwarded-Proto`를 Django로 전달하도록 설정한다.
4. Django에 `SECURE_PROXY_SSL_HEADER`를 추가한다.
5. 그 다음 아래 값을 `True`로 전환한다.

```text
DJANGO_SECURE_SSL_REDIRECT
DJANGO_SESSION_COOKIE_SECURE
DJANGO_CSRF_COOKIE_SECURE
```

HTTPS 인프라 준비 없이 위 값을 먼저 켜면 로그인, 리다이렉트, 폼 제출이 깨질 수 있다.

## 6. 현재 코드 기준 권장 정리 항목

- `WEB` 런타임 `.env`에서 `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`는 제거하는 쪽이 안전하다.
- `WEB`와 `AI` 모두 운영 도메인 기준의 `APP_BASE_URL`, `FASTAPI_INTERNAL_CHAT_URL`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`를 명확하게 관리해야 한다.
- `AI` workflow도 `WEB`처럼 rerun 시 새 EB application version을 생성하도록 버전 라벨 재사용 방지를 적용하는 것을 권장한다.

## 7. 운영 전환 직전 확인 순서

1. 운영 도메인과 인증서 준비
2. `WEB` / `AI` GitHub Secrets 입력
3. 테스트용 EB 이름과 Docker 이미지 이름 교체
4. 배포 브랜치 정책 확정
5. HTTPS 프록시 설정 반영
6. 운영 환경 첫 배포
7. `/health/` 확인
8. OAuth 로그인 확인
9. Django -> FastAPI 내부 호출 확인
10. 정적 파일 및 이미지 업로드 동작 확인
