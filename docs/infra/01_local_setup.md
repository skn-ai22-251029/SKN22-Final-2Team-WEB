# 로컬 환경 구성 가이드

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

## 3. 로컬 실행

### 전체 스택 실행

```bash
cd infra
docker compose up -d
```

처음 실행 시 DockerHub에서 이미지를 pull한다.

### 코드 수정 후 반영

```bash
cd infra
docker compose build django   # 또는 fastapi
docker compose up -d
```

### down이 필요한 경우

```bash
# .env 환경변수 변경 시
docker compose down && docker compose up -d

# 볼륨(DB) 초기화가 필요할 때 (데이터 날아감 주의)
docker compose down -v && docker compose up -d
```

### 서비스 직접 실행 (핫리로드, 빠른 개발)

> `infra/.env`의 `POSTGRES_HOST=postgres` → `POSTGRES_HOST=localhost`로 변경 후 실행

```bash
# DB만 Docker로 실행
cd infra && docker compose up -d postgres

# Django (터미널 1)
cd services/django
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# FastAPI (터미널 2)
cd services/fastapi
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 접속 주소

| 서비스 | 주소 |
|---|---|
| TailTalk | http://localhost |
| Django Admin | http://localhost/admin/ |
| Django API | http://localhost/api/ |
| FastAPI Docs | http://localhost/docs |

### 첫 실행 시 Django 슈퍼유저 생성

```bash
docker compose run --rm django python manage.py createsuperuser
```

---

## 4. 자주 쓰는 명령어

```bash
# 컨테이너 상태 확인
docker compose ps

# 특정 서비스 로그 보기
docker compose logs -f django
docker compose logs -f fastapi

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

## 5. 트러블슈팅

### 포트가 이미 사용 중이라는 오류

```bash
# 사용 중인 포트 확인 (예: 5432)
lsof -i :5432
# 해당 프로세스 종료 후 다시 실행
docker compose up -d
```

### 컨테이너가 계속 재시작되는 경우

```bash
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
