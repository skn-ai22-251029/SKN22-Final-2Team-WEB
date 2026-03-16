# 백엔드 인프라 설정 가이드

> **프로젝트명**: TailTalk
> **대상 파일**: `infra/docker-compose.yml`, `infra/docker-compose.override.yml`

---

## 1. 전체 요청 흐름

### 로컬 개발

```
사용자
  │
  ├─ localhost:3000  → Frontend (Next.js)
  ├─ localhost:8000  → Django API
  ├─ localhost:8001  → FastAPI
  ├─ localhost:5432  → PostgreSQL
  └─ localhost:6333  → Qdrant
```

> nginx는 개발 환경에서 사용하지 않는다. 각 서비스 포트에 직접 접근한다.

### 프로덕션 (EC2)

```
사용자 (HTTP)
  │
  ▼
EC2 · Nginx :80
  ├─ /              → frontend:3000
  ├─ /api/django/   → django:8000   (gunicorn + WSGI)
  └─ /api/chat/     → fastapi:8001  (uvicorn + ASGI)
```

> SSL은 도메인 확정 후 Cloudflare + Origin Certificate로 적용 예정.

---

## 2. 서비스 구성

| 서비스 | 이미지/빌드 | 포트(내부) | 설명 |
|---|---|---|---|
| `django` | `services/django` | 8000 | Auth / User / Pet / Order API |
| `fastapi` | `services/fastapi` | 8001 | 챗봇 / 추천 마이크로서비스 |
| `frontend` | `services/frontend` | 3000 | Next.js SSR |
| `postgres` | `postgres:16` | 5432 | 관계형 DB |
| `qdrant` | `qdrant/qdrant` | 6333 | Vector DB |
| `nginx` | `nginx:alpine` | 80 | 리버스 프록시 (프로덕션 전용) |
| `jenkins` | `jenkins/jenkins:lts` | 8080 | 보류 — GitHub Actions로 대체 |

> 모든 서비스는 `platform: linux/amd64`로 고정 (EC2 x86_64 대응).
> Apple Silicon 로컬 개발 시 Rosetta 에뮬레이션으로 빌드됨.

---

## 3. WSGI / ASGI

| | WSGI | ASGI |
|--|------|------|
| 대상 | Django | FastAPI |
| 서버 | gunicorn | uvicorn |
| 방식 | 동기 | 비동기 |
| 실행 | `gunicorn config.wsgi:application` | `uvicorn main:app` |

---

## 4. 환경 변수 설정

```bash
cp infra/.env.example infra/.env
# POSTGRES_PASSWORD, DJANGO_SECRET_KEY 필수 입력
```

`DJANGO_SECRET_KEY` 생성:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

`infra/.env` 항목:

```env
# PostgreSQL
POSTGRES_DB=tailtalk_db
POSTGRES_USER=mungnyang
POSTGRES_PASSWORD=
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Django
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost

# FastAPI
FASTAPI_ENV=development

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

---

## 5. 로컬 개발 환경 실행

`docker-compose.override.yml`이 자동으로 적용되어 각 서비스 포트가 호스트에 바인딩된다.

```bash
cd infra
docker compose up -d --build
```

### 특정 서비스만 실행

```bash
docker compose up -d postgres qdrant django
```

### 로그 확인

```bash
docker compose logs -f django
docker compose logs -f fastapi
```

### Django 관리 명령

```bash
# 마이그레이션 파일 생성
docker compose run --rm django python manage.py makemigrations

# 마이그레이션 적용
docker compose run --rm django python manage.py migrate

# 슈퍼유저 생성
docker compose run --rm django python manage.py createsuperuser
```

> DB 초기화는 `sql/schema.sql`이 아닌 **Django ORM migrations**으로 관리한다.

### 컨테이너 정리

```bash
# 컨테이너 중지 및 제거
docker compose down

# 볼륨까지 제거 (DB 초기화)
docker compose down -v
```

---

## 6. 프로덕션 배포 (EC2)

`docker-compose.override.yml`을 제외하고 실행. nginx가 80포트로 트래픽을 수신하여 라우팅한다.

```bash
cd infra
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml exec django python manage.py migrate --noinput
docker compose -f docker-compose.yml exec django python manage.py collectstatic --noinput
```

### Nginx 라우팅

```nginx
upstream django   { server django:8000; }
upstream fastapi  { server fastapi:8001; }
upstream frontend { server frontend:3000; }

server {
    listen 80;

    location / {
        proxy_pass http://frontend;
    }

    location /api/django/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api/chat/ {
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # WebSocket 지원 (스트리밍 응답)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 7. GitHub Actions CI/CD

워크플로우 파일: `.github/workflows/ci-cd.yml`

### 트리거

| 이벤트 | 브랜치 | 실행 Job |
|---|---|---|
| `push` | `develop` | Build & Test |
| `pull_request` | `develop` | Build & Test |
| `push` | `main` | Build & Test → Deploy to EC2 |

### Job 흐름

```
[Build & Test]
  1. Checkout
  2. .env 생성 (Secrets에서 주입)
  3. docker compose build
  4. docker compose run --rm django python manage.py test
  5. docker compose down -v

[Deploy to EC2] — main 브랜치 push 시만
  1. SSH로 EC2 접속
  2. git pull origin main
  3. docker compose -f infra/docker-compose.yml up -d --build
  4. python manage.py migrate
  5. python manage.py collectstatic
```

### GitHub Secrets 등록

`upstream 레포 → Settings → Secrets and variables → Actions`

| Secret | 설명 |
|---|---|
| `DJANGO_SECRET_KEY` | Django 시크릿 키 |
| `POSTGRES_DB` | DB 이름 |
| `POSTGRES_USER` | DB 유저 |
| `POSTGRES_PASSWORD` | DB 패스워드 |
| `EC2_HOST` | EC2 퍼블릭 IP (Elastic IP) |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | EC2 키페어 private key 전체 내용 |

---

## 8. 완료 조건 체크리스트

- [ ] `docker compose up --build` 오류 없이 실행
- [ ] `http://localhost:8000/admin/` Django Admin 접근 확인
- [ ] `http://localhost:8001/docs` FastAPI Swagger 접근 확인
- [ ] `http://localhost:3000` Next.js 인덱스 페이지 확인
- [ ] Django migrations 정상 적용 확인
- [ ] GitHub Actions CI 파이프라인 정상 동작 확인
