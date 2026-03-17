# 개발 환경 시작 가이드

> TailTalk 프로젝트에 처음 합류한 팀원을 위한 빠른 시작 가이드

---

## 1. 사전 준비

### 개발 환경

> **Windows 사용자**: WSL2 + Docker Desktop 조합을 권장한다.
> WSL2 안에서 레포 클론 및 모든 작업을 진행한다.

**WSL2 설치 (Windows)**
```powershell
# PowerShell (관리자)
wsl --install
# 재부팅 후 Ubuntu 터미널에서 작업
```

**Docker Desktop 설정 (Windows)**
- Docker Desktop 설치 후 Settings → Resources → WSL Integration → Ubuntu 활성화

### 필수 설치

| 도구 | 설치 방법 |
|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 설치 후 실행해두기 |
| [Git](https://git-scm.com/) | `git --version` 으로 확인 |

> Docker Desktop이 실행 중이어야 `docker compose`가 동작한다.

### 레포지토리 설정

**1. upstream 레포 fork**

GitHub에서 `skn-ai22-251029/SKN22-Final-2Team-WEB` → **Fork** 버튼 클릭

**2. fork 클론**

```bash
git clone https://github.com/<내_GitHub_ID>/SKN22-Final-2Team-WEB.git
cd SKN22-Final-2Team-WEB
```

**3. upstream remote 추가**

```bash
git remote add upstream https://github.com/skn-ai22-251029/SKN22-Final-2Team-WEB.git
git remote -v  # 확인
```

---

## 2. 환경 변수 설정

```bash
cp infra/.env.example infra/.env
```

`infra/.env` 파일을 열어 아래 항목을 채운다:

```env
POSTGRES_PASSWORD=원하는_패스워드
DJANGO_SECRET_KEY=아래_명령어로_생성
```

`DJANGO_SECRET_KEY` 생성:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

나머지 항목은 기본값 그대로 사용해도 된다.

---

## 3. DB 데이터 복원

데이터 적재는 한 명이 완료한 후 덤프 파일을 공유한다.
**팀 공유 드라이브에서 아래 파일을 받아 레포 루트에 놓는다:**

- `tailtalk_dump.sql` — PostgreSQL 전체 덤프 (상품 3,800개 / 리뷰 전체)
- `qdrant_products.snapshot` — Qdrant products 컬렉션 스냅샷 (3,618개)

### PostgreSQL 복원

```bash
# 1. DB 컨테이너 실행
cd infra && docker compose up -d postgres

# 2. 마이그레이션 먼저 적용 (테이블 스키마 생성)
docker compose run --rm django python manage.py migrate

# 3. 덤프 복원 (레포 루트에서 실행)
docker exec -i tailtalk-postgres-1 psql -U mungnyang -d tailtalk_db < tailtalk_dump.sql
```

### Qdrant 복원

```bash
# 1. Qdrant 컨테이너 실행
cd infra && docker compose up -d qdrant

# 2. 스냅샷 파일을 컨테이너에 복사 (레포 루트에서 실행)
docker cp qdrant_products.snapshot tailtalk-qdrant-1:/qdrant/snapshots/

# 3. 스냅샷으로 컬렉션 복원
curl -X PUT "http://localhost:6333/collections/products/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d '{"location": "/qdrant/snapshots/qdrant_products.snapshot"}'

# 4. 복원 확인
curl -s "http://localhost:6333/collections/products" | python3 -m json.tool
```

> `points_count: 3618`, `status: green` 이면 정상.

---

### 덤프 파일 재생성 (데이터 담당자만)

Gold ETL 결과가 변경됐을 때만 재생성한다.

```bash
# PostgreSQL dump
docker exec tailtalk-postgres-1 pg_dump -U mungnyang tailtalk_db > tailtalk_dump.sql

# Qdrant snapshot
docker exec tailtalk-fastapi-1 python3 -c "
from qdrant_client import QdrantClient
snap = QdrantClient(url='http://qdrant:6333').create_snapshot('products')
print(snap.name)
"
# 출력된 파일명으로 복사
docker cp tailtalk-qdrant-1:/qdrant/snapshots/products/<출력된_파일명> qdrant_products.snapshot
```

> 재생성 후 팀 공유 드라이브 파일 교체 및 팀 공지 필요.

---

## 4. 로컬 실행

개발할 때는 **DB만 Docker로 올리고, 서비스는 직접 실행**하는 방식을 사용한다.
매번 재빌드 없이 핫리로드로 빠르게 개발할 수 있다.

### DB 컨테이너 실행

```bash
cd infra
docker compose up -d postgres qdrant
```

### 서비스 직접 실행

> `infra/.env`의 `POSTGRES_HOST=postgres` → `POSTGRES_HOST=localhost`로 변경 후 실행

```bash
# Django (터미널 1)
cd services/django
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# FastAPI (터미널 2)
cd services/fastapi
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Frontend (터미널 3)
cd services/frontend
npm install
npm run dev
```

### 통합 테스트 / 배포 전 확인 — 전체 Docker Compose

```bash
cd infra
docker compose up -d --build
```

처음 실행 시 이미지 빌드로 5~10분 소요될 수 있다.

### 접속 주소

| 서비스 | 주소 | 설명 |
|---|---|---|
| Frontend | http://localhost:3000 | Next.js 화면 |
| Django Admin | http://localhost:8000/admin/ | 관리자 페이지 |
| Django API | http://localhost:8000/api/ | REST API |
| FastAPI Docs | http://localhost:8001/docs | Swagger UI |

### 첫 실행 시 Django 슈퍼유저 생성

```bash
# 방법 1
python manage.py createsuperuser

# 방법 2 (Docker)
docker compose run --rm django python manage.py createsuperuser
```

---

## 5. 브랜치 전략

### 기본 규칙

- 모든 작업은 **이슈 번호로 브랜치**를 따서 시작
- `develop` 브랜치에 PR로 머지 (직접 push 금지)
- `main` 브랜치는 배포 전용 — 건드리지 않는다

### 브랜치 이름 규칙

```
feature/<이슈번호>-<설명>   # 새 기능
fix/<이슈번호>-<설명>       # 버그 수정
docs/<이슈번호>-<설명>      # 문서 작업
```

예시: `feature/12-user-login`, `fix/34-auth-token-bug`

### 작업 흐름

```
1. GitHub에서 이슈 생성 또는 확인
2. upstream/develop 최신화 후 브랜치 생성
3. 작업 후 커밋
4. fork에 push → upstream/develop으로 PR 생성
5. 리뷰 후 머지
```

```bash
# upstream 최신화
git fetch upstream
git checkout develop
git merge upstream/develop
git push origin develop

# 브랜치 생성
git checkout -b feature/12-user-login

# 작업 후 커밋
git add .
git commit -m "feat(auth): add login API"

# fork에 push 후 GitHub에서 upstream/develop으로 PR 생성
git push origin feature/12-user-login
```

> **CI/CD 참고**: fork PR → upstream/develop 은 빌드 자동 검증 없음.
> develop 머지 후 push 이벤트에서 Build & Test 실행됨.

### 커밋 메시지 형식

```
<type>(<scope>): <설명>
```

| type | 용도 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서 |
| `refactor` | 리팩토링 |
| `test` | 테스트 |
| `chore` | 빌드/설정 |

---

## 6. 자주 쓰는 명령어

```bash
# 컨테이너 상태 확인
docker compose ps

# 특정 서비스 로그 보기
docker compose logs -f django
docker compose logs -f fastapi
docker compose logs -f frontend

# 특정 서비스만 재시작
docker compose restart django

# 컨테이너 중지
docker compose down

# 컨테이너 + DB 볼륨까지 초기화 (DB 날아감 주의)
docker compose down -v

# Django 마이그레이션
docker compose run --rm django python manage.py makemigrations
docker compose run --rm django python manage.py migrate
```

---

## 7. 트러블슈팅

### 포트가 이미 사용 중이라는 오류

로컬에서 이미 같은 포트를 쓰는 프로세스가 있을 때 발생한다.

```bash
# 사용 중인 포트 확인 (예: 5432)
lsof -i :5432

# 해당 프로세스 종료 후 다시 실행
docker compose up -d
```

### 컨테이너가 계속 재시작되는 경우

```bash
# 로그로 원인 확인
docker compose logs django
```

### DB 연결 오류

`infra/.env`의 `POSTGRES_*` 값이 올바른지 확인. 변경 후 재시작:

```bash
docker compose down && docker compose up -d
```

### 이미지 빌드 캐시 문제

```bash
docker compose build --no-cache
docker compose up -d
```

---

## 8. 역할별 작업 디렉토리

| 역할 | 작업 경로 | 로컬 포트 |
|---|---|---|
| Frontend | `services/frontend/` | http://localhost:3000 |
| Django (Auth/API) | `services/django/` | http://localhost:8000 |
| FastAPI (챗봇/추천) | `services/fastapi/` | http://localhost:8001 |
| 인프라 공통 | `infra/` | — |

> 본인 담당 서비스 외 디렉토리는 되도록 건드리지 않는다.
> 공통 설정(`infra/docker-compose.yml`, `.env.example` 등) 변경 시 팀에 공유할 것.

---

## 9. CI/CD

### 흐름

```
코드 push / PR
  │
  ▼
[GitHub Actions] Build & Test
  │  develop, main 모두 실행
  │
  ▼ (main push 시에만)
[GitHub Actions] Docker Hub push
  │  leemdo/tailtalk-django:latest
  │  leemdo/tailtalk-fastapi:latest
  │  leemdo/tailtalk-frontend:latest
  │
  ▼
[EC2] docker pull → docker compose up -d
```

> 빌드는 GitHub Actions에서 수행. EC2는 이미지 pull + 실행만 한다.

### 트리거

| 이벤트 | 브랜치 | 실행 |
|---|---|---|
| `push` / `pull_request` | `develop` | Build & Test |
| `push` | `main` | Build & Test → Docker Hub push → EC2 배포 |

### 배포 주소

- http://tailtalk.leemdo.com

상세 내용: `docs/infra/04_github_actions_guide.md`
