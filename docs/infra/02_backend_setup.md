# 백엔드 인프라 설정 가이드

> Docker Compose 기반 전체 서비스 구성, SSL, Nginx 리버스 프록시

---

## 1. 전체 요청 흐름

```
사용자
  │ HTTPS
  ▼
Cloudflare (SSL Termination — Full Strict)
  │ HTTPS (Origin Certificate)
  ▼
EC2 · Nginx :443
  ├─ /          → Next.js  :3000
  ├─ /api/      → Django   :8000  (gunicorn + WSGI)
  ├─ /chat/     → FastAPI  :8001  (uvicorn + ASGI)
  └─ jenkins.*  → Jenkins  :8080
```

---

## 2. SSL — Cloudflare Full Strict + Origin Certificate

| 설정 항목 | 값 |
|-----------|-----|
| DNS Proxy | 활성화 (오렌지 구름 ☁️) |
| SSL/TLS 모드 | **Full (Strict)** |
| HTTP→HTTPS 리디렉션 | Cloudflare Edge Rules에서 설정 |

Cloudflare Origin Certificate는 Cloudflare 대시보드에서 무료 발급. EC2 Nginx에 적용.
Cloudflare를 통해서만 유효한 인증서이므로 Cloudflare DNS Proxy가 항상 활성화되어 있어야 함.

**Origin Certificate 발급 및 적용**

```bash
# 1. Cloudflare 대시보드 → SSL/TLS → Origin Server → Create Certificate
# 2. 발급된 인증서/키 EC2에 저장
sudo mkdir -p /etc/ssl/cloudflare
sudo vi /etc/ssl/cloudflare/cert.pem   # 인증서 붙여넣기
sudo vi /etc/ssl/cloudflare/key.pem    # 개인키 붙여넣기
```

```nginx
# nginx/nginx.conf — SSL 적용
server {
    listen 443 ssl;
    ssl_certificate     /etc/ssl/cloudflare/cert.pem;
    ssl_certificate_key /etc/ssl/cloudflare/key.pem;
    ...
}
```

---

## 3. WSGI / ASGI 개념

| | WSGI | ASGI |
|--|------|------|
| 대상 | Django | FastAPI |
| 서버 | **gunicorn** | **uvicorn** |
| 방식 | 동기 | 비동기 |
| 실행 예 | `gunicorn config.wsgi:application` | `uvicorn main:app` |

Nginx는 이 두 프로세스 앞에서 트래픽을 분기하는 리버스 프록시 역할만 함.

---

## 4. Docker Compose 서비스 구성

```yaml
# docker-compose.yml (전체 구조)
services:
  nginx:       # 리버스 프록시 — 포트 80 (외부 노출)
  django:      # Auth/User/Pet/Order API — 포트 8000 (내부)
  fastapi:     # 챗봇/추천 API — 포트 8001 (내부)
  frontend:    # Next.js — 포트 3000 (내부)
  postgres:    # PostgreSQL 16 — 포트 5432 (내부)
  qdrant:      # Vector DB — 포트 6333 (내부)
  jenkins:     # CI/CD — 포트 8080 (내부, jenkins 서브도메인으로 노출)
  airflow:     # DAG 오케스트레이션 — 포트 8082 (내부, TBD)
```

> 외부 노출 포트는 Nginx(:80)만. 나머지는 내부 Docker 네트워크로만 통신.

---

## 5. Nginx 라우팅 설정

```nginx
# nginx/nginx.conf

upstream django  { server django:8000; }
upstream fastapi { server fastapi:8001; }
upstream frontend { server frontend:3000; }

server {
    listen 80;
    server_name example.com www.example.com;

    # Next.js
    location / {
        proxy_pass http://frontend;
    }

    # Django REST API
    location /api/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # FastAPI (챗봇)
    location /chat/ {
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # WebSocket 지원 (스트리밍 응답)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Jenkins — 서브도메인 분리
server {
    listen 80;
    server_name jenkins.example.com;

    location / {
        proxy_pass http://jenkins:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 6. 환경 변수 (.env)

`.env.example` 참고. 실제 `.env`는 `.gitignore`에 등록되어 있음.

```env
# PostgreSQL
POSTGRES_DB=skn22
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Django
DJANGO_SECRET_KEY=your_secret_key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com

# FastAPI
FASTAPI_ENV=production

# JWT
JWT_SECRET_KEY=your_jwt_secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
KAKAO_CLIENT_ID=
KAKAO_CLIENT_SECRET=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=

# AI
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

---

## 7. PostgreSQL 초기 스키마 적용

`sql/schema.sql`을 postgres 컨테이너 초기화 시 자동 적용:

```yaml
# docker-compose.yml
postgres:
  image: postgres:16
  volumes:
    - ./sql/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    - postgres_data:/var/lib/postgresql/data
  environment:
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

> `/docker-entrypoint-initdb.d/`에 마운트된 `.sql` 파일은 DB 최초 생성 시 자동 실행됨.

---

## 8. Jenkins

```yaml
# docker-compose.yml
jenkins:
  image: jenkins/jenkins:lts
  volumes:
    - jenkins_data:/var/jenkins_home
    - /var/run/docker.sock:/var/run/docker.sock  # Docker in Docker
  environment:
    - JAVA_OPTS=-Djenkins.install.runSetupWizard=false
```

> `/var/run/docker.sock` 마운트로 Jenkins가 호스트 Docker 제어 가능 → 배포 파이프라인에서 `docker compose` 명령 실행 가능.

---

## 9. 완료 조건 체크리스트

- [ ] `docker compose up --build` 오류 없이 실행
- [ ] `http://localhost/api/admin/` Django Admin 접근 확인
- [ ] `http://localhost/chat/docs` FastAPI Swagger 접근 확인
- [ ] PostgreSQL `schema.sql` 테이블 생성 확인
- [ ] Jenkins `http://jenkins.localhost/` 접근 확인
