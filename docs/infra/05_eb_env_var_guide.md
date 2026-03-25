# 테스트 배포 환경 `.env` 및 EB 환경변수 정리

## 목적

이 문서는 현재 테스트 배포 구조에서 아래 두 가지를 구분해서 정리한 문서이다.

1. 배포 zip 내부의 `.env` 파일에 들어가야 하는 값
2. Elastic Beanstalk 환경에 등록해 두어야 하는 환경변수 key

현재 기준 배포 대상:

- Django + nginx: `test-tailtalk-django-env`
- FastAPI: `test-tailtalk-fastapi-env`

## 핵심 원칙

현재 CI/CD 구조에서는 배포 zip 안의 `.env`에는 주로 **이미지 태그**만 넣고, 실제 운영 설정값은 **Elastic Beanstalk 환경변수**로 관리하는 방식이다.

즉:

- 배포 zip `.env` = 어떤 Docker 이미지를 띄울지
- EB 환경변수 = 앱이 실제로 실행될 때 필요한 설정값

## 1. 배포 zip 안 `.env`에 필요한 값

### nginx 폴더

nginx는 현재 별도 `.env`가 필요하지 않다.

이유:

- `deploy/eb/test-django/nginx/nginx.conf`는 환경변수를 읽지 않음
- nginx 컨테이너는 정적 설정 파일만 마운트해서 사용함

즉, nginx 폴더에는 `.env`가 필요 없다.

### Django 배포 폴더

현재 구조에서 Django 배포 zip 내부 `.env`에 최소한 필요한 값은 아래 하나다.

```text
DJANGO_IMAGE=<도커허브_이미지:태그>
```

예시:

```text
DJANGO_IMAGE=kimheejoon91/test-tailtalk-django:72a1915
```

현재 CI/CD도 이 방식으로 `.env`를 생성해서 zip에 포함한다.

### FastAPI 배포 폴더

현재 구조에서 FastAPI 배포 zip 내부 `.env`에 최소한 필요한 값은 아래 하나다.

```text
FASTAPI_IMAGE=<도커허브_이미지:태그>
```

예시:

```text
FASTAPI_IMAGE=kimheejoon91/test-tailtalk-fastapi:b3bba0d
```

현재 CI/CD도 이 방식으로 `.env`를 생성해서 zip에 포함한다.

## 2. Elastic Beanstalk 환경에 등록해야 하는 환경변수

아래는 **애플리케이션 실행에 필요한 값**이며, 배포 zip `.env`가 아니라 **Elastic Beanstalk 환경변수**에 넣어 두는 것을 기준으로 정리했다.

---

## Django + nginx 환경에 등록할 변수

대상 환경:

- `test-tailtalk-django-env`

### 필수

아래 값들은 현재 Django 설정상 사실상 필수다.

```text
DJANGO_SECRET_KEY
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
FASTAPI_INTERNAL_CHAT_URL
INTERNAL_SERVICE_TOKEN
```

설명:

- `DJANGO_SECRET_KEY`: Django 앱 실행 필수
- `POSTGRES_DB`: PostgreSQL DB 이름
- `POSTGRES_USER`: PostgreSQL 사용자명
- `POSTGRES_PASSWORD`: PostgreSQL 비밀번호
- `POSTGRES_HOST`: PostgreSQL 호스트
- `FASTAPI_INTERNAL_CHAT_URL`: Django가 FastAPI 내부 API를 호출할 주소
- `INTERNAL_SERVICE_TOKEN`: Django와 FastAPI 간 내부 인증 토큰

### 권장

아래 값들은 운영 편의를 위해 넣는 것이 좋다.

```text
DJANGO_ALLOWED_HOSTS
POSTGRES_PORT
APP_BASE_URL
DJANGO_DEBUG
CORS_ALLOWED_ORIGINS
DJANGO_SECURE_SSL_REDIRECT
DJANGO_SESSION_COOKIE_SECURE
DJANGO_CSRF_COOKIE_SECURE
SOCIAL_AUTH_REQUESTS_TIMEOUT
```

설명:

- `DJANGO_ALLOWED_HOSTS`: 기본값은 `*`지만 명시하는 편이 안전함
- `POSTGRES_PORT`: 기본값은 `5432`
- `APP_BASE_URL`: OAuth 콜백 URL 생성에 중요
- `DJANGO_DEBUG`: 기본값은 `False`
- `CORS_ALLOWED_ORIGINS`: 프론트엔드 도메인 허용 시 필요
- `DJANGO_SECURE_SSL_REDIRECT`: HTTPS 리다이렉트 여부
- `DJANGO_SESSION_COOKIE_SECURE`: 세션 쿠키 보안 설정
- `DJANGO_CSRF_COOKIE_SECURE`: CSRF 쿠키 보안 설정
- `SOCIAL_AUTH_REQUESTS_TIMEOUT`: 소셜 로그인 API 타임아웃, 기본값 `10`

### OAuth 사용 시 필수

소셜 로그인 기능을 사용할 경우 아래 값들을 반드시 등록해야 한다.

```text
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
KAKAO_CLIENT_ID
KAKAO_CLIENT_SECRET
```

주의:

- OAuth 키가 없으면 `/auth/<provider>/start/`는 라우트는 살아 있어도 정상 로그인 진행이 안 됨
- `APP_BASE_URL`이 비어 있으면 콜백 URL이 의도와 다르게 생성될 수 있음

### S3 업로드 사용 시 필요

사용하는 경우에만 넣으면 된다.

```text
AWS_S3_BUCKET_NAME
AWS_S3_REGION_NAME
AWS_S3_CUSTOM_DOMAIN
AWS_S3_ENDPOINT_URL
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

현재 코드 기준으로는 S3 관련 기능이 항상 강제되지는 않는다.

### 선택

```text
USE_SQLITE
SQLITE_NAME
```

설명:

- 테스트나 임시 환경에서 PostgreSQL 대신 SQLite를 사용할 때만 필요
- 현재 배포 구조에서는 일반적으로 사용하지 않음

---

## FastAPI 환경에 등록할 변수

대상 환경:

- `test-tailtalk-fastapi-env`

### 필수

현재 Docker Compose 기준으로 최소한 아래 값들은 준비되어 있어야 한다.

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
INTERNAL_SERVICE_TOKEN
```

설명:

- `POSTGRES_DB`: PostgreSQL DB 이름
- `POSTGRES_USER`: PostgreSQL 사용자명
- `POSTGRES_PASSWORD`: PostgreSQL 비밀번호
- `POSTGRES_HOST`: PostgreSQL 호스트
- `INTERNAL_SERVICE_TOKEN`: Django와 FastAPI 간 내부 인증 토큰

### 권장

```text
POSTGRES_PORT
OPENAI_API_KEY
QDRANT_HOST
QDRANT_PORT
```

설명:

- `POSTGRES_PORT`: 기본값은 `5432`
- `OPENAI_API_KEY`: OpenAI 호출 기능 사용 시 필요
- `QDRANT_HOST`: Qdrant 사용 시 필요
- `QDRANT_PORT`: 기본값은 `6333`

주의:

- 기능에 따라 `OPENAI_API_KEY`, `QDRANT_HOST`, `QDRANT_PORT`가 없으면 일부 API가 정상 동작하지 않을 수 있음
- 현재 compose 파일에서는 기본값이 있어 컨테이너는 뜰 수 있지만, 실제 기능은 제한될 수 있음

---

## 3. 현재 구조 기준 권장 운영 방식

현재 구조에서는 아래처럼 운영하는 것이 가장 명확하다.

### 배포 zip `.env`

- Django: `DJANGO_IMAGE`만 포함
- FastAPI: `FASTAPI_IMAGE`만 포함
- nginx: `.env` 없음

### EB 환경변수

- 앱 실행에 필요한 실제 값 전부 등록
- DB 접속 정보
- 내부 인증 토큰
- OAuth 키
- OpenAI 키
- 기타 운영 설정값

## 4. 예시

### Django 배포 zip용 `.env`

```text
DJANGO_IMAGE=kimheejoon91/test-tailtalk-django:72a1915
```

### FastAPI 배포 zip용 `.env`

```text
FASTAPI_IMAGE=kimheejoon91/test-tailtalk-fastapi:b3bba0d
```

### Django EB 환경변수 예시

```text
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*
APP_BASE_URL=https://test-tailtalk-django-env.eba-idn3t8gh.ap-northeast-2.elasticbeanstalk.com
POSTGRES_DB=tailtalk
POSTGRES_USER=tailtalk
POSTGRES_PASSWORD=...
POSTGRES_HOST=...
POSTGRES_PORT=5432
FASTAPI_INTERNAL_CHAT_URL=http://test-tailtalk-fastapi-env.eba-5ymgtjp9.ap-northeast-2.elasticbeanstalk.com/api/chat/
INTERNAL_SERVICE_TOKEN=...
CORS_ALLOWED_ORIGINS=
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
KAKAO_CLIENT_ID=...
KAKAO_CLIENT_SECRET=...
```

### FastAPI EB 환경변수 예시

```text
POSTGRES_DB=tailtalk
POSTGRES_USER=tailtalk
POSTGRES_PASSWORD=...
POSTGRES_HOST=...
POSTGRES_PORT=5432
INTERNAL_SERVICE_TOKEN=...
OPENAI_API_KEY=...
QDRANT_HOST=...
QDRANT_PORT=6333
```

## 5. 한 줄 정리

현재 테스트 배포 구조에서는 **배포 zip 안 `.env`에는 이미지 태그만 넣고**, 실제 앱 실행에 필요한 값은 **Elastic Beanstalk 환경변수에 등록하는 방식**으로 관리하면 된다.
