# CI/CD와 EB 환경변수 정리

> 작성 일자: 2026-04-08 KST  
> 목적: 배포 zip에 `.env`를 포함하지 않는 구조로 전환할 때, GitHub Secrets와 Elastic Beanstalk Environment properties에 필요한 환경변수 이름을 정리한다.  
> 주의: 이 문서에는 실제 secret 값을 기록하지 않는다.

## 1. 기준

GitHub Secrets는 CI/CD가 AWS에 접속하고 EB 환경변수를 설정하는 데 사용한다.

EB Environment properties는 Django/FastAPI 앱이 런타임에 읽는 값이다.

목표 구조:

```text
GitHub Secrets
  -> GitHub Actions
  -> EB Environment properties 설정
  -> EB runtime 환경변수
  -> Django / FastAPI 앱
```

배포 zip에는 `.env`를 포함하지 않는다.

## 2. WEB GitHub Repo Secrets

WEB 저장소 GitHub Secrets에 필요한 필수 값:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT

DJANGO_SECRET_KEY
FASTAPI_INTERNAL_CHAT_URL
FASTAPI_INTERNAL_RECOMMEND_URL
```

WEB 저장소 GitHub Secrets에 필요한 선택 값:

```text
DJANGO_ALLOWED_HOSTS
APP_BASE_URL
INTERNAL_SERVICE_TOKEN
CORS_ALLOWED_ORIGINS
DJANGO_SECURE_SSL_REDIRECT
DJANGO_SESSION_COOKIE_SECURE
DJANGO_CSRF_COOKIE_SECURE
DJANGO_CSRF_TRUSTED_ORIGINS

AWS_S3_BUCKET_NAME
AWS_S3_CUSTOM_DOMAIN
AWS_S3_ENDPOINT_URL

GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
KAKAO_CLIENT_ID
KAKAO_CLIENT_SECRET

JUSO_CONFIRM_KEY
FASTAPI_STREAM_CONNECT_TIMEOUT
FASTAPI_STREAM_READ_TIMEOUT
FASTAPI_STREAM_WRITE_TIMEOUT
FASTAPI_STREAM_POOL_TIMEOUT
```

`AWS_S3_REGION_NAME`은 현재 workflow에서 `ap-northeast-2`로 하드코딩할 수 있으므로 secret이 아니어도 된다.

## 3. Django EB Environment Properties

Django EB 환경에 설정할 값:

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT

DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS
APP_BASE_URL
FASTAPI_INTERNAL_CHAT_URL
FASTAPI_INTERNAL_RECOMMEND_URL
INTERNAL_SERVICE_TOKEN
CORS_ALLOWED_ORIGINS
DJANGO_SECURE_SSL_REDIRECT
DJANGO_SESSION_COOKIE_SECURE
DJANGO_CSRF_COOKIE_SECURE
DJANGO_CSRF_TRUSTED_ORIGINS

GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
KAKAO_CLIENT_ID
KAKAO_CLIENT_SECRET
```

S3를 Django 앱에서 사용할 경우:

```text
AWS_S3_BUCKET_NAME
AWS_S3_REGION_NAME
AWS_S3_CUSTOM_DOMAIN
AWS_S3_ENDPOINT_URL
```

S3 접근에 access key를 직접 사용할 경우:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

가능하면 S3 접근용 key는 EB instance profile 또는 IAM role로 대체한다.

## 4. AI GitHub Repo Secrets

AI/FastAPI 저장소 GitHub Secrets에 필요한 필수 값:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT

OPENAI_API_KEY
```

AI/FastAPI 저장소 GitHub Secrets에 필요한 선택 값:

```text
LANGSMITH_TRACING
LANGSMITH_API_KEY
LANGSMITH_PROJECT
LANGSMITH_ENDPOINT
LANGSMITH_WORKSPACE_ID

INTERNAL_SERVICE_TOKEN
OPENAI_TIMEOUT_SECONDS
POSTGRES_CONNECT_TIMEOUT_SECONDS
POSTGRES_STATEMENT_TIMEOUT_MS
FASTEMBED_MODEL
FASTEMBED_CACHE_PATH
FASTEMBED_LOCAL_FILES_ONLY
FASTEMBED_AUTO_DISABLE_LOW_MEMORY
FASTAPI_UVICORN_WORKERS
```

## 5. FastAPI EB Environment Properties

FastAPI EB 환경에 설정할 값은 AI/FastAPI 저장소 GitHub Secrets 기준과 동일하다. 필수 런타임 값은 `POSTGRES_*`, `OPENAI_API_KEY`이고, LangSmith/timeout/FastEmbed/내부 토큰 값은 필요한 경우 추가한다.

## 6. 전환 시 주의점

변경 후 workflow는 다음 방식으로 동작한다.

```text
1. GitHub Actions에서 EB Environment properties를 설정한다.
2. 배포 zip에서 .env를 제거한다.
3. docker-compose.yml 검증에는 dummy 값만 담은 .env.check를 사용한다.
4. .env.check도 배포 zip에는 포함하지 않는다.
5. docker-compose.yml은 ${VAR} 환경변수 참조를 유지한다.
6. Django/FastAPI 앱은 기존처럼 환경변수를 읽는다.
```

workflow는 필수 값이 없으면 실패하고, 선택 값은 GitHub Secrets 값이 비어 있으면 EB 기존 값을 덮어쓰지 않는다.

AWS Elastic Beanstalk Docker Compose 환경에서는 EB 환경 속성으로 설정한 값을 기반으로 `.env`를 생성할 수 있다. 단, 배포 번들에 `.env`를 포함하면 EB가 `.env`를 생성하지 않는다.
