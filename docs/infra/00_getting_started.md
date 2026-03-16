# 개발 환경 시작 가이드

> TailTalk 프로젝트에 처음 합류한 팀원을 위한 빠른 시작 가이드

---

## 1. 사전 준비

### 필수 설치

| 도구 | 설치 방법 |
|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 설치 후 실행해두기 |
| [Git](https://git-scm.com/) | `git --version` 으로 확인 |

> Docker Desktop이 실행 중이어야 `docker compose`가 동작한다.

### 레포지토리 클론

```bash
git clone https://github.com/skn-ai22-251029/SKN22-Final-2Team-WEB.git
cd SKN22-Final-2Team-WEB
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

## 3. 로컬 실행

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
docker compose run --rm django python manage.py createsuperuser
```

---

## 4. 브랜치 전략

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
2. develop에서 브랜치 생성
3. 작업 후 커밋
4. develop으로 PR 생성
5. 리뷰 후 머지
```

```bash
# 브랜치 생성
git checkout develop
git pull origin develop
git checkout -b feature/12-user-login

# 작업 후 커밋
git add .
git commit -m "feat(auth): add login API"

# push 후 GitHub에서 PR 생성
git push origin feature/12-user-login
```

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

## 5. 자주 쓰는 명령어

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

## 6. 트러블슈팅

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

## 7. 역할별 작업 디렉토리

| 역할 | 작업 경로 | 로컬 포트 |
|---|---|---|
| Frontend | `services/frontend/` | http://localhost:3000 |
| Django (Auth/API) | `services/django/` | http://localhost:8000 |
| FastAPI (챗봇/추천) | `services/fastapi/` | http://localhost:8001 |
| 인프라 공통 | `infra/` | — |

> 본인 담당 서비스 외 디렉토리는 되도록 건드리지 않는다.
> 공통 설정(`infra/docker-compose.yml`, `.env.example` 등) 변경 시 팀에 공유할 것.

---

## 8. CI/CD

PR을 `develop`에 올리면 **자동으로 Build & Test**가 실행된다.
`main`에 머지되면 **EC2 자동 배포**까지 진행된다.

- 배포 주소: http://tailtalk.leemdo.com

상세 내용: `docs/infra/04_github_actions_guide.md`
