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

**권장 관리 기준**:
- Django 런타임 값은 `WEB repo GitHub Secrets -> django-deploy.zip 내부 .env` 한 곳으로만 관리한다.
- 동일한 키를 EB 환경변수에 중복 등록하지 않는다.
- GitHub Actions가 이미지 푸시와 Elastic Beanstalk 배포에서만 쓰는 값은 `.env`에 넣지 않는다.

**Zip 파일 구성** (`django-deploy.zip`):
```
django-deploy.zip
├─ docker-compose.yml  (이미지 참조, 환경변수 템플릿)
├─ .env  ✅ (GitHub Secrets에서 읽어서 생성해야 함)
└─ nginx/
   ├─ nginx.conf
   └─ ...
```

**WEB repo GitHub Secrets 분류**:

`.env` 생성용:
```bash
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
DJANGO_SECRET_KEY
INTERNAL_SERVICE_TOKEN
AWS_S3_BUCKET_NAME
AWS_S3_CUSTOM_DOMAIN
AWS_S3_ENDPOINT_URL
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
KAKAO_CLIENT_ID
KAKAO_CLIENT_SECRET
```

`GitHub Actions` 전용:
```bash
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

**생성되는 `.env` 내용**:
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

GOOGLE_CLIENT_ID=${{ secrets.GOOGLE_CLIENT_ID }}
GOOGLE_CLIENT_SECRET=${{ secrets.GOOGLE_CLIENT_SECRET }}
NAVER_CLIENT_ID=${{ secrets.NAVER_CLIENT_ID }}
NAVER_CLIENT_SECRET=${{ secrets.NAVER_CLIENT_SECRET }}
KAKAO_CLIENT_ID=${{ secrets.KAKAO_CLIENT_ID }}
KAKAO_CLIENT_SECRET=${{ secrets.KAKAO_CLIENT_SECRET }}
```

**중요한 구분**:
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`는 WEB의 GitHub Actions가 Docker 이미지 푸시와 Elastic Beanstalk 배포 API를 호출할 때만 사용한다.
- 현재 Django 런타임 `.env`에는 `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`를 넣지 않는다.
- 현재 Django 코드에서 S3 업로드는 비활성화되어 있으므로 런타임 IAM 키가 필요하지 않다.
- 추후 Django가 런타임 AWS 자격증명을 다시 써야 하면, 같은 이름을 중복 사용하지 말고 IAM Role 또는 별도 runtime secret 이름으로 분리한다.

---

#### 🤖 AI 배포 (`test-tailtalk-fastapi-env`)

**읽는 곳**: `GitHub Secrets`

**생성되는 파일**: `.deploy-fastapi/.env`

**권장 관리 기준**:
- FastAPI 런타임 값은 `AI repo GitHub Secrets -> fastapi-deploy.zip 내부 .env` 한 곳으로만 관리한다.
- private Docker 이미지 pull 인증은 `DOCKERHUB_*` GitHub Secrets를 기준으로 하고, 배포 시 `DOCKER_USERNAME`, `DOCKER_PASSWORD`를 EB 환경변수로 자동 주입한다.
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`는 GitHub Actions가 이미지 푸시와 Elastic Beanstalk 배포 API를 호출할 때만 사용한다.

**Zip 파일 구성** (`fastapi-deploy.zip`):
```
fastapi-deploy.zip
├─ docker-compose.yml  ✅ (이미지 참조, 환경변수 템플릿)
├─ .env  ✅ (GitHub Secrets에서 읽어서 생성)
├─ .ebextensions/
│  └─ 00_private_registry_env.config  ✅ (DOCKER_USERNAME/DOCKER_PASSWORD를 EB 환경변수로 주입)
└─ .platform/
   ├─ hooks/prebuild/01_docker_login.sh       ✅ (이미지 pull 전 docker login)
   └─ confighooks/prebuild/01_docker_login.sh ✅ (config deploy 시 동일 처리)
```

**AI repo GitHub Secrets 분류**:

`.env` 생성용:
```bash
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
```

`GitHub Actions` 전용:
```bash
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

`배포 시 EB 환경변수로 자동 생성`:
```bash
DOCKER_USERNAME   ← DOCKERHUB_USERNAME 에서 생성
DOCKER_PASSWORD   ← DOCKERHUB_TOKEN 에서 생성
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

**별도로 사용하는 GitHub Secrets**:
```bash
DOCKERHUB_USERNAME=${{ secrets.DOCKERHUB_USERNAME }}
DOCKERHUB_TOKEN=${{ secrets.DOCKERHUB_TOKEN }}
AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }}
AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**중요한 구분**:
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`는 GitHub Actions가 Elastic Beanstalk 배포/검증 API를 호출할 때만 사용한다.
- 따라서 `AWS_*` 값은 FastAPI 컨테이너 런타임 `.env`에 넣지 않는다.
- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`도 FastAPI 애플리케이션 런타임 `.env`에는 넣지 않는다.
- 대신 CI/CD가 `.ebextensions/00_private_registry_env.config`를 생성해 `DOCKER_USERNAME`, `DOCKER_PASSWORD`를 EB 환경변수로 주입하고, `.platform/hooks/prebuild/01_docker_login.sh`에서 이미지 pull 전에 `docker login`을 수행한다.

---

### Step 4: EB 배포 및 실행

#### 🌐 WEB (test-tailtalk-django-env) - Nginx + Django

**배포되는 환경**:
- EC2 인스턴스에서 docker-compose 실행
- 배포 .env 파일을 마운트
- EB 환경변수는 중복 없이 최소화

**권장 EB 환경변수**:
```
# 없음
```

같은 키를 `.env`와 EB 환경변수에 동시에 두면 값 drift와 우선순위 혼선이 생길 수 있다.
따라서 WEB은 `GitHub Secrets -> 배포 .env`만 사용하고, EB에는 동일 키를 중복 등록하지 않는 방식을 권장한다.

**작동 방식**:
1. zip 파일 다운로드
2. docker-compose.yml + .env 파일을 /var/app/current/ 에 추출
3. `docker-compose up -d` 실행
4. 변수 관리 원칙:
   - Django 컨테이너에 필요한 값은 배포된 `.env` 한 곳만 사용
   - `DOCKERHUB_*`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`는 GitHub Actions 전용
   - 동일 키는 EB 환경변수에 중복 등록하지 않음

---

#### 🤖 AI (test-tailtalk-fastapi-env) - FastAPI

**배포되는 환경**:
- EC2 인스턴스에서 docker-compose 실행
- 배포 .env 파일을 마운트
- EB 환경변수는 이미지 pull 인증에 필요한 최소값만 자동 주입

**권장 EB 환경변수**:
```
DOCKER_USERNAME=(배포 시 .ebextensions 로 자동 주입)
DOCKER_PASSWORD=(배포 시 .ebextensions 로 자동 주입)
```

**참고**:
- FastAPI 애플리케이션 런타임 값은 배포된 `.env`에서 읽는다.
- `DOCKER_USERNAME`, `DOCKER_PASSWORD`는 private Docker 이미지 다운로드를 위한 배포 보조용 환경변수다.
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`는 GitHub Actions 배포 자격증명이라 EB/FastAPI 런타임 환경변수 목록에는 포함하지 않는다.
- 현재 EB 환경에 `POSTGRES_*`, `OPENAI_API_KEY`, `LANGSMITH_*`, `DOCKERHUB_*`가 남아 있더라도 이는 과거 수동 설정 잔재일 수 있으며, 권장 구조는 아니다.

**작동 방식**:
1. zip 파일 다운로드
2. docker-compose.yml + .env 파일을 /var/app/current/ 에 추출
3. `docker-compose up -d` 실행
4. 변수 관리 원칙:
   - FastAPI 컨테이너에 필요한 값은 배포된 `.env` 한 곳만 사용
   - `DOCKERHUB_*`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`는 GitHub Actions 전용
   - `DOCKER_USERNAME`, `DOCKER_PASSWORD`만 EB 환경변수로 자동 주입
   - 동일한 런타임 키는 EB 환경변수에 중복 등록하지 않음

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
LANGSMITH_PROJECT      → (LangSmith 프로젝트명)
LANGSMITH_ENDPOINT     → https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID → (워크스페이스 ID)
```

### 배포 자격증명
```
DOCKERHUB_USERNAME     → (DockerHub 사용자명 - CI push / EB pull 인증용)
DOCKERHUB_TOKEN        → (DockerHub Personal Access Token - CI push / EB pull 인증용)
AWS_ACCESS_KEY_ID      → (AWS IAM 액세스 키)
AWS_SECRET_ACCESS_KEY  → (AWS IAM 시크릿 키)
```
**⚠️ 주의**: DOCKERHUB_USERNAME과 DOCKERHUB_TOKEN은 GitHub Actions가 이미지를 푸시할 때 사용하고, 배포 시 `DOCKER_USERNAME`, `DOCKER_PASSWORD`로 변환되어 EB 인스턴스의 이미지 다운로드에 사용됩니다.

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
- [ ] `test-tailtalk-django-env` 중복 환경변수 제거
- [ ] `test-tailtalk-fastapi-env` 중복 환경변수 제거

### CI/CD 파일
- [ ] `.github/workflows/ci-cd.yml` 배포 번들에 `.env`, `.ebextensions`, `.platform` 포함 ✅ (FastAPI)
- [ ] `.github/workflows/ci-cd.yml` Django 배포 번들에 `.env`, `.ebextensions` 포함 ✅

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
  - docker/login-action 으로 Docker Hub 로그인
  - .ebextensions/00_private_registry_env.config 생성
  - deploy/eb/test-fastapi/.platform 디렉토리를 배포 zip에 포함
  - AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 로 EB 배포 실행
  ```

**4단계**: prebuild hook 확인
- `deploy/eb/test-fastapi/.platform/hooks/prebuild/01_docker_login.sh` 와
  `deploy/eb/test-fastapi/.platform/confighooks/prebuild/01_docker_login.sh` 가 존재하는지 확인:
  ```yaml
  if [[ -z "${DOCKER_USERNAME:-}" || -z "${DOCKER_PASSWORD:-}" ]]; then
    exit 1
  fi
  echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin
  ```

**5단계**: EB 환경변수 반영 확인
- 배포 후 `test-tailtalk-fastapi-env` 환경에 `DOCKER_USERNAME`, `DOCKER_PASSWORD`가 반영되었는지 확인

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
