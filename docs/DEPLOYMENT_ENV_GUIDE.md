# 🚀 배포 환경 설정 가이드

## 📋 개요

본 프로젝트는 두 개의 독립적인 Elastic Beanstalk 환경에 배포됩니다:

1. **WEB 서비스** (`test-tailtalk-django-env`)
   - Nginx + Django
   - SKN22-Final-2Team-WEB 저장소

2. **AI 서비스** (`test-tailtalk-fastapi-env`)
   - FastAPI
   - SKN22-Final-2Team-AI 저장소 (서브모듈)

---

## 🔄 배포 단계별 환경변수 흐름

### Step 1: 로컬 개발 환경

#### `infra/.env` (Docker Compose 로컬 실행)
```bash
# 🔗 데이터베이스 (로컬 postgres 컨테이너)
POSTGRES_DB=tailtalk_db
POSTGRES_USER=mungnyang
POSTGRES_PASSWORD=  # 로컬에서는 간단한 값
POSTGRES_HOST=postgres  # docker-compose 서비스명
POSTGRES_PORT=5432

# 🔐 Django 설정
DJANGO_SECRET_KEY=  # 로컬 테스트용 간단한 값
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# 🌐 응용 프로그램
APP_BASE_URL=http://localhost:8000
FASTAPI_INTERNAL_CHAT_URL=http://fastapi:8001/api/chat/
INTERNAL_SERVICE_TOKEN=dev-internal-token
CORS_ALLOWED_ORIGINS=http://localhost
DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_SESSION_COOKIE_SECURE=False
DJANGO_CSRF_COOKIE_SECURE=False

# ☁️ AWS (선택사항 - 로컬 테스트)
AWS_S3_BUCKET_NAME=
AWS_S3_REGION_NAME=ap-northeast-2
AWS_S3_CUSTOM_DOMAIN=
AWS_S3_ENDPOINT_URL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# 🔌 Social OAuth (선택사항)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
KAKAO_CLIENT_ID=
KAKAO_CLIENT_SECRET=
SOCIAL_AUTH_REQUESTS_TIMEOUT=10

# 🔌 FastAPI  설정
FASTAPI_ENV=development
OPENAI_API_KEY=  # 로컬에서는 테스트 키
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=tailtalk-fastapi-local
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=
```

#### `services/django/.env` (선택사항 - Django 직접 실행)
```bash
# 🔗 데이터베이스 (로컬 직접 연결)
POSTGRES_DB=tailtalk_db
POSTGRES_USER=mungnyang
POSTGRES_PASSWORD=  # 로컬에서는 보안 불필요
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# 🔐 Django
DJANGO_SECRET_KEY=  # 로컬 테스트용
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# 🌐 기타
CORS_ALLOWED_ORIGINS=http://localhost
APP_BASE_URL=http://localhost:8000
```

#### `services/fastapi/.env` (선택사항 - FastAPI 직접 실행)
```bash
# 🔗 데이터베이스
POSTGRES_HOST=localhost
POSTGRES_DB=tailtalk_db
POSTGRES_USER=mungnyang
POSTGRES_PASSWORD=

# 🔑 API 키 (선택사항)
OPENAI_API_KEY=
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=tailtalk-fastapi-local
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=
```

---

### Step 2: GitHub Actions CI/CD - 이미지 빌드

**읽는 곳**: `Dockerfile` ENV + 테스트 환경 변수

#### Django 이미지 빌드
- Dockerfile: `services/django/Dockerfile`
- 빌드 인자로 environment 설정
- CI 환경에서 테스트용 .env 로드

#### FastAPI 이미지 빌드
- Dockerfile: `services/fastapi/Dockerfile`
- 빌드 인자로 environment 설정
- CI 환경에서 테스트용 .env 로드

---

### Step 3: 배포 번들 생성

#### 🌐 WEB 배포 (`test-tailtalk-django-env`)

**읽는 곳**: `GitHub Secrets`

**생성되는 파일**: `.deploy-django/.env`

**Zip 파일 구성** (`django-deploy.zip`):
```
django-deploy.zip
├─ docker-compose.yml  (이미지 참조, 환경변수 템플릿)
├─ .env  ✅ (GitHub Secrets에서 읽어서 생성해야 함)
└─ nginx/
   ├─ nginx.conf
   └─ ...
```

**생성해야 할 .env 내용**:
```bash
# 이 파일은 CI/CD가 GitHub Secrets에서 읽어서 자동 생성
POSTGRES_DB=${{ secrets.POSTGRES_DB }}
POSTGRES_USER=${{ secrets.POSTGRES_USER }}
POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
POSTGRES_HOST=${{ secrets.POSTGRES_HOST }}
POSTGRES_PORT=${{ secrets.POSTGRES_PORT || 5432 }}

DJANGO_SECRET_KEY=${{ secrets.DJANGO_SECRET_KEY }}
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*.elasticbeanstalk.com
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True

APP_BASE_URL=http://test-tailtalk-django-env.ap-northeast-2.elasticbeanstalk.com
FASTAPI_INTERNAL_CHAT_URL=http://test-tailtalk-fastapi-env.ap-northeast-2.elasticbeanstalk.com/api/chat/
INTERNAL_SERVICE_TOKEN=${{ secrets.INTERNAL_SERVICE_TOKEN || 'prod-token' }}
CORS_ALLOWED_ORIGINS=*

AWS_S3_BUCKET_NAME=${{ secrets.AWS_S3_BUCKET_NAME }}
AWS_S3_REGION_NAME=ap-northeast-2
AWS_S3_CUSTOM_DOMAIN=${{ secrets.AWS_S3_CUSTOM_DOMAIN }}
AWS_S3_ENDPOINT_URL=${{ secrets.AWS_S3_ENDPOINT_URL }}
AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }}
AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }}

GOOGLE_CLIENT_ID=${{ secrets.GOOGLE_CLIENT_ID }}
GOOGLE_CLIENT_SECRET=${{ secrets.GOOGLE_CLIENT_SECRET }}
NAVER_CLIENT_ID=${{ secrets.NAVER_CLIENT_ID }}
NAVER_CLIENT_SECRET=${{ secrets.NAVER_CLIENT_SECRET }}
KAKAO_CLIENT_ID=${{ secrets.KAKAO_CLIENT_ID }}
KAKAO_CLIENT_SECRET=${{ secrets.KAKAO_CLIENT_SECRET }}
```

---

#### 🤖 AI 배포 (`test-tailtalk-fastapi-env`)

**읽는 곳**: `GitHub Secrets`

**생성되는 파일**: `.deploy-fastapi/.env`

**Zip 파일 구성** (`fastapi-deploy.zip`):
```
fastapi-deploy.zip
├─ docker-compose.yml  (이미지 참조, 환경변수 템플릿)
└─ .env  ✅ (GitHub Secrets에서 읽어서 생성 - 이미 구현됨)
```

**생성되는 .env 내용**:
```bash
# 이 파일은 CI/CD가 GitHub Secrets에서 읽어서 자동 생성
POSTGRES_DB=${{ secrets.POSTGRES_DB }}
POSTGRES_USER=${{ secrets.POSTGRES_USER }}
POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
POSTGRES_HOST=${{ secrets.POSTGRES_HOST }}
POSTGRES_PORT=${{ secrets.POSTGRES_PORT || 5432 }}

OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
LANGSMITH_TRACING=${{ secrets.LANGSMITH_TRACING || 'false' }}
LANGSMITH_API_KEY=${{ secrets.LANGSMITH_API_KEY }}
LANGSMITH_PROJECT=${{ secrets.LANGSMITH_PROJECT }}
LANGSMITH_ENDPOINT=${{ secrets.LANGSMITH_ENDPOINT }}
LANGSMITH_WORKSPACE_ID=${{ secrets.LANGSMITH_WORKSPACE_ID }}
```

---

### Step 4: EB 배포 및 실행

#### 🌐 WEB (test-tailtalk-django-env) - Nginx + Django

**배포되는 환경**:
- EC2 인스턴스에서 docker-compose 실행
- 배포 .env 파일을 마운트
- EB 환경변수로 추가 설정 (보조)

**EB 환경변수에 설정된 값** (현재):
```
POSTGRES_HOST=test-tailtalk-postgres-v2.cpkmaq4eqdte.ap-northeast-2.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=tailtalk_prod
POSTGRES_USER=(RDS 설정값)
POSTGRES_PASSWORD=(RDS 설정값)

DJANGO_DEBUG=False
DJANGO_SECRET_KEY=(프로덕션 시크릿)
DJANGO_ALLOWED_HOSTS=*.elasticbeanstalk.com

... (기타 모든 OAuth, AWS 설정)
```

**작동 방식**:
1. zip 파일 다운로드
2. docker-compose.yml + .env 파일을 /var/app/current/ 에 추출
3. `docker-compose up -d` 실행
4. 환경변수 로드 순서:
   - 1순위: 배포된 .env 파일 (가장 중요)
   - 2순위: EB 환경변수 설정값 (보조)

---

#### 🤖 AI (test-tailtalk-fastapi-env) - FastAPI

**배포되는 환경**:
- EC2 인스턴스에서 docker-compose 실행
- 배포 .env 파일을 마운트
- EB 환경변수로 추가 설정 (보조)

**EB 환경변수에 설정된 값** (현재):
```
POSTGRES_HOST=test-tailtalk-postgres-v2.cpkmaq4eqdte.ap-northeast-2.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=tailtalk_prod
POSTGRES_USER=(RDS 설정값)
POSTGRES_PASSWORD=(RDS 설정값)

OPENAI_API_KEY=(OpenAI 키)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=(LangSmith 키)
LANGSMITH_PROJECT=tailtalk-fastapi-prod
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=(워크스페이스 ID)
```

**작동 방식**:
1. zip 파일 다운로드
2. docker-compose.yml + .env 파일을 /var/app/current/ 에 추출
3. `docker-compose up -d` 실행
4. 환경변수 로드는 동일한 우선순위

---

## 📊 GitHub Secrets 설정 목록

### 데이터베이스 (공용)
```
POSTGRES_HOST          → test-tailtalk-postgres-v2.*.rds.amazonaws.com
POSTGRES_PORT          → 5432
POSTGRES_DB            → tailtalk_prod
POSTGRES_USER          → (RDS 설정값)
POSTGRES_PASSWORD      → (RDS 설정값)
```

### API 키
```
OPENAI_API_KEY         → sk-proj-...
LANGSMITH_API_KEY      → lsv2_pt_...
LANGSMITH_PROJECT      → tailtalk-fastapi-prod
LANGSMITH_ENDPOINT     → https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID → (워크스페이스 ID)
```

### 배포 자격증명
```
DOCKERHUB_USERNAME     → (DockerHub 사용자명 - EB 이미지 다운로드시 필수)
DOCKERHUB_TOKEN        → (DockerHub Personal Access Token - EB 이미지 다운로드시 필수)
AWS_ACCESS_KEY_ID      → (AWS IAM 액세스 키)
AWS_SECRET_ACCESS_KEY  → (AWS IAM 시크릿 키)
```
**⚠️ 주의**: DOCKERHUB_USERNAME과 DOCKERHUB_TOKEN은 EB 인스턴스가 Docker Hub에서 이미지를 다운로드할 때 필수입니다. CI/CD 빌드 단계에서 이미지를 푸시할 때도 필요합니다.

### Django 전용
```
DJANGO_SECRET_KEY      → (프로덕션 Django 시크릿)
GOOGLE_CLIENT_ID       → (구글 OAuth)
GOOGLE_CLIENT_SECRET   → (구글 OAuth)
NAVER_CLIENT_ID        → (네이버 OAuth)
NAVER_CLIENT_SECRET    → (네이버 OAuth)
KAKAO_CLIENT_ID        → (카카오 OAuth)
KAKAO_CLIENT_SECRET    → (카카오 OAuth)
```

---

## ✅ 환경변수 설정 체크리스트

### 로컬 개발
- [ ] `infra/.env` 파일 생성
- [ ] `services/django/.env` (선택사항)
- [ ] `services/fastapi/.env` (선택사항)

### GitHub 설정
- [ ] 데이터베이스 5개 Secrets 저장
- [ ] API 키 5개 Secrets 저장
- [ ] 배포 자격증명 4개 Secrets 저장
- [ ] Django 전용 설정값 Secrets 저장

### AWS EB 환경
- [ ] `test-tailtalk-django-env` 환경변수 설정
- [ ] `test-tailtalk-fastapi-env` 환경변수 설정

### CI/CD 파일
- [ ] `.github/workflows/ci-cd.yml` 배포 번들에 .env 포함 ✅ (FastAPI)
- [ ] `.github/workflows/ci-cd.yml` Django 배포 번들에 .env 포함 ⚠️ (필요)

---

## 🔧 문제 해결

### 배포 실패 - Docker 이미지 다운로드 실패
**증상**: EB 배포 중 "Instance deployment failed to download the Docker image" 오류

**근본 원인**: EC2 인스턴스가 Docker Hub에서 Docker 이미지를 다운로드할 수 없음
- 이미지가 비공개인 경우 인증 정보 필요
- Docker Hub 자격증명이 제대로 설정되지 않음

**해결방법**:

**1단계**: GitHub Secrets 확인
```bash
# GitHub Repository Settings → Secrets and variables → Actions 에서 아래 확인:
✅ DOCKERHUB_USERNAME (예: kimheejoon91)
✅ DOCKERHUB_TOKEN (Docker Hub Personal Access Token)
```

**2단계**: Docker Hub 토큰 생성 (필요시)
```bash
# Docker Hub > Account Settings > Security > New Access Token 생성
# 토큰 권한: Read, Write 필요
```

**3단계**: CI/CD 워크플로우 확인
- FastAPI: `.github/workflows/ci-cd.yml` 에서 다음 포함 확인:
  ```yaml
  DOCKER_USERNAME=${{ secrets.DOCKERHUB_USERNAME }}
  DOCKER_PASSWORD=${{ secrets.DOCKERHUB_TOKEN }}
  ```

**4단계**: docker-compose.yml 확인
- `deploy/eb/test-fastapi/docker-compose.yml` 에 인증 정보 포함 확인:
  ```yaml
  services:
    fastapi:
      auth:
        username: ${DOCKER_USERNAME}
        password: ${DOCKER_PASSWORD}
  ```

**대안**: 이미지를 공개로 설정
- Docker Hub 리포지토리를 공개로 변경하여 임시로 인증 우회
- 테스트 후 다시 비공개로 변경 권장

---

### 배포 실패 - 환경변수 미로드
**증상**: EB 배포 후 애플리케이션이 시작되지 않음

**원인**: 배포 .env 파일에 필수 환경변수가 없음

**해결방법**:
1. CI/CD가 GitHub Secrets에서 값을 제대로 읽고 있는지 확인
2. 배포 zip 파일에 .env 파일이 포함되어 있는지 확인
3. EB에서 zip 추출 로그 확인

### API 키 오류
**증상**: OpenAI/LangSmith API 호출 실패

**원인**: GitHub Secrets에 API 키가 없거나 잘못된 값

**해결방법**:
1. 正确的 API 키가 GitHub Secrets에 저장되어 있는지 확인
2. CI/CD가 Secrets를 올바르게 읽고 있는지 확인

### 데이터베이스 연결 실패
**증상**: POSTGRES_* 환경변수 관련 오류

**원인**: RDS 엔드포인트, 자격증명 오류

**해결방법**:
1. RDS 엔드포인트가 정확한지 확인
2. RDS 보안 그룹이 EB EC2 인스턴스를 허용하는지 확인
3. GitHub Secrets의 POSTGRES_* 값이 RDS 설정과 일치하는지 확인

---

## 📝 참고사항

- 로컬 `.env` 파일은 `.gitignore`에 포함되어 커밋되지 않습니다
- 프로덕션 환경의 민감정보(API 키, 비밀번호)는 GitHub Secrets에만 저장됩니다
- EB 배포 시 GitHub Secrets→배포 .env→docker-compose 순서로 환경변수가 로드됩니다
- 각 EB 환경 (`django`, `fastapi`)은 독립적으로 작동하며, 서로 영향을 주지 않습니다
