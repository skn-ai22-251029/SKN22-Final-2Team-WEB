# Docker 이미지 빌드 컨텍스트 정리 가이드

## 목적

이 문서는 현재 배포 시 빌드되는 Django/FastAPI 이미지에 운영과 무관한 파일이 포함되는 지점을 정리하고,
어떤 파일을 어떻게 수정하면 되는지 실행 가능한 수준으로 정리한 가이드다.

핵심 목표는 아래 3가지다.

- 운영 이미지에 테스트, 문서, 예전 코드, 보조 `.env` 파일이 들어가지 않게 한다.
- 필요한 런타임 파일만 명시적으로 복사하도록 빌드 과정을 단순화한다.
- 검증 절차를 표준화해서 이후에 같은 문제가 다시 생기지 않게 한다.

## 현재 확인 결과

확인 기준일: `2026-04-03`

실제 `docker buildx build`로 `COPY . .` 결과를 로컬 디렉터리로 추출해서 확인했다.

### Django

- 배포 이미지 빌드 컨텍스트: `services/django`
- 배포 Dockerfile: `services/django/Dockerfile`
- 현재 문제 지점:
  - `COPY . .` 사용
  - `.dockerignore`의 `tests/` 패턴은 최상위 `tests/` 폴더만 대상으로 해서 `chat/tests.py`, `orders/tests.py` 같은 파일은 제외하지 못함
- 실제 포함 확인 파일 예시:
  - `chat/tests.py`
  - `orders/tests.py`
  - `pets/tests.py`
  - `users/tests.py`
  - `config/test_settings.py`
  - `Dockerfile`
- 다만 Django 쪽은 전체 복사 결과가 약 `1.3MB` 수준이라 영향은 상대적으로 작다.

### FastAPI

- 실제 배포 이미지는 FastAPI 서브모듈 저장소의 workflow에서 빌드됨
- 배포 이미지 빌드 컨텍스트: FastAPI 저장소 루트 `.`
  웹 저장소 안에서는 `services/fastapi` 경로에 해당
- 배포 Dockerfile: `services/fastapi/Dockerfile`
- 현재 문제 지점:
  - `COPY . .` 사용
  - `.dockerignore`가 중첩 `.env`와 중첩 `tests`를 충분히 막지 못함
- 실제 포함 확인 파일/폴더 예시:
  - `.github/`
  - `.test-deploy/.env`
  - `before/`
  - `docs/`
  - `deploy/`
  - `test/`
  - `final_ai/tests/`
  - `README.md`
  - `LICENSE`
  - `pyrightconfig.json`
  - `test_pet_switch.py`
- FastAPI 복사 결과는 약 `2.2MB`였고, 지금은 크기보다도 "운영에 필요 없는 파일이 이미지에 들어간다"는 점이 더 큰 문제다.

## 왜 이런 일이 생기는가

현재 두 서비스 모두 Dockerfile 마지막에 `COPY . .`를 사용한다.

즉, 실제로 이미지 안에 들어가는 파일 범위는 아래 두 가지로 결정된다.

1. 빌드 컨텍스트
2. `.dockerignore`로 제외되지 않은 나머지 파일

따라서 문제를 줄이는 방법은 아래 둘 중 하나다.

1. `.dockerignore`를 강화해서 컨텍스트 자체를 줄인다.
2. Dockerfile에서 필요한 경로만 명시적으로 `COPY`한다.

권장 방식은 서비스별로 다르다.

- FastAPI: `.dockerignore` 강화 + Dockerfile allowlist `COPY`를 함께 적용
- Django: 우선 `.dockerignore` 강화, 필요 시에만 allowlist `COPY`로 전환

## 수정 원칙

### 1. 런타임 파일만 이미지에 넣는다

이미지 안에 있어야 하는 것은 아래 정도로 한정하는 것이 맞다.

#### Django

- `manage.py`
- `config/`
- `chat/`
- `orders/`
- `pets/`
- `products/`
- `users/`
- `templates/`
- `static/`
- `requirements.txt`

#### FastAPI

- `main.py`
- `final_ai/`
- `scripts/`
- `requirements.txt`

### 2. 배포 보조 파일은 이미지에 넣지 않는다

아래는 Git checkout에는 남아 있어도 되지만, Docker 이미지에는 들어가면 안 된다.

- 문서: `docs/`, `README.md`, `LICENSE`
- 테스트: `test/`, `tests/`, `**/tests.py`, `config/test_settings.py`
- 예전 코드/보관 코드: `before/`
- CI/CD 파일: `.github/`
- 로컬 배포 보조 파일: `.test-deploy/`, `deploy/`
- 예시/보조 env: `.env.example`, `**/.env`, `**/.env.*`

### 3. `.dockerignore`는 "중첩 경로"까지 막아야 한다

현재 `services/fastapi/.test-deploy/.env`가 이미지에 들어간 이유는
`.dockerignore`의 `.env`, `.env.*` 패턴만으로는 하위 디렉터리의 `.env`를 충분히 막지 못했기 때문이다.

따라서 아래처럼 중첩 경로 패턴을 함께 두는 편이 안전하다.

```dockerignore
**/.env
**/.env.*
**/tests/
**/tests.py
```

## 권장 수정안

### 1. FastAPI 먼저 정리

중요도: 가장 높음

이 작업은 웹 저장소가 아니라 FastAPI 서브모듈 저장소 기준으로 수정해야 한다.
웹 저장소에서 보이는 경로는 `services/fastapi/...` 이지만, 실제 PR/배포는 FastAPI 저장소에서 진행된다.

### 1-1. `.dockerignore` 강화

수정 대상:

- 웹 저장소 기준: `services/fastapi/.dockerignore`
- FastAPI 저장소 기준: `.dockerignore`

권장 예시는 아래와 같다.

```dockerignore
# env
.env
.env.*
**/.env
**/.env.*
.env.example

# git / editor / local cache
.git
.gitignore
.dockerignore
.github/
.idea/
.vscode/
.DS_Store

# python cache / test cache
.venv/
venv/
__pycache__/
**/__pycache__/
*.py[cod]
*.pyo
.pytest_cache/
.ruff_cache/
.mypy_cache/
.tox/
.nox/
.coverage
.coverage.*
htmlcov/
coverage.xml
build/
dist/
*.egg-info/

# runtime unnecessary files
*.log
Dockerfile
README.md
LICENSE
pyrightconfig.json
docs/
deploy/
.test-deploy/
before/

# test assets
test/
tests/
**/tests/
**/tests.py
**/test_*.py
final_ai/tests/
test_pet_switch.py
```

주의:

- `scripts/`는 제외하면 안 된다. `prewarm_fastembed.py`가 필요하다.
- `final_ai/pipeline/data/`는 제외하면 안 된다. 현재 런타임 데이터가 들어 있다.
- `.dockerignore`는 Docker build 컨텍스트에만 영향이 있고, GitHub Actions의 zip 배포 번들 생성이나 일반 `cp` 명령에는 영향이 없다.

### 1-2. Dockerfile을 allowlist `COPY` 방식으로 변경

수정 대상:

- 웹 저장소 기준: `services/fastapi/Dockerfile`
- FastAPI 저장소 기준: `Dockerfile`

현재는 아래 부분이 문제다.

```dockerfile
COPY . .
```

권장 수정 예시는 아래와 같다.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_MODEL=intfloat/multilingual-e5-large \
    FASTEMBED_CACHE_PATH=/opt/fastembed-cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY final_ai ./final_ai
COPY scripts ./scripts

ARG PREWARM_FASTEMBED=1
RUN if [ "$PREWARM_FASTEMBED" = "1" ]; then python scripts/prewarm_fastembed.py; fi

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
```

이렇게 바꾸면 아래가 같이 해결된다.

- `COPY . .`로 인한 불필요 파일 유입 차단
- `Dockerfile`이나 `.github`, `docs` 같은 파일이 실수로 이미지에 들어가는 문제 차단
- 이후 새 문서/테스트 폴더가 추가돼도 운영 이미지가 자동으로 비대해지는 문제 완화

### 1-3. FastAPI CI에 "이미지 내용 검증" 추가

수정 대상:

- 웹 저장소 기준: `services/fastapi/.github/workflows/ci-cd.yml`
- FastAPI 저장소 기준: `.github/workflows/ci-cd.yml`

현재 CI는 이미지가 빌드되고 앱이 뜨는지만 보며, 불필요 파일이 들어갔는지는 확인하지 않는다.

아래 같은 검증 step을 추가하는 것을 권장한다.

```yaml
- name: Verify runtime image does not contain non-runtime files
  run: |
    docker run --rm tailtalk-fastapi:ci sh -lc '
      test ! -d /app/docs &&
      test ! -d /app/test &&
      test ! -d /app/before &&
      test ! -d /app/deploy &&
      test ! -d /app/.github &&
      test ! -e /app/.test-deploy/.env
    '
```

이 step을 넣으면 이후 누군가가 `.dockerignore`를 느슨하게 바꾸거나 `COPY . .`를 되살려도 CI에서 바로 잡을 수 있다.

### 2. Django는 `.dockerignore` 먼저 강화

중요도: 중간

Django 쪽은 현재도 과도하게 큰 이미지는 아니지만, 테스트 전용 파일과 `Dockerfile`이 함께 들어가고 있다.
이 정도는 지금 바로 정리해 두는 편이 좋다.

### 2-1. `.dockerignore` 보강

수정 대상:

- `services/django/.dockerignore`

권장 추가 항목:

```dockerignore
# env
**/.env
**/.env.*
.env.example

# prevent Dockerfile itself from being copied by COPY . .
Dockerfile

# test files
**/tests.py
**/test_*.py
config/test_settings.py
```

즉 현재 파일에 아래 의도를 추가하면 된다.

- 하위 폴더 `.env` 차단
- `COPY . .` 시 `Dockerfile` 자체가 이미지에 들어가지 않도록 차단
- 각 앱의 `tests.py`와 `config/test_settings.py` 차단

### 2-2. Django Dockerfile은 우선 유지 가능

수정 대상:

- `services/django/Dockerfile`

현재 Django는 앱 디렉터리가 여러 개라서 FastAPI처럼 allowlist `COPY`로 바꾸면 통제력은 높아지지만, 새 앱이 추가될 때 Dockerfile도 함께 수정해야 한다.

따라서 Django는 아래 순서로 가는 것을 권장한다.

1. 먼저 `.dockerignore` 보강
2. 그래도 이미지 구성 관리가 불안하면 그때 allowlist `COPY`로 전환

예를 들어 정말 더 엄격하게 가고 싶다면 아래처럼 바꿀 수는 있다.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py .
COPY config ./config
COPY chat ./chat
COPY orders ./orders
COPY pets ./pets
COPY products ./products
COPY users ./users
COPY templates ./templates
COPY static ./static
```

다만 이 방식은 새 앱 디렉터리가 추가될 때 누락 위험이 있으므로, 지금 단계에서는 필수는 아니다.

## 구현 순서

서브모듈 규칙까지 고려하면 아래 순서가 안전하다.

1. FastAPI 저장소에서 `.dockerignore`, `Dockerfile`, CI 검증 step 수정
2. FastAPI 저장소에서 이미지 빌드 및 `/health` 검증
3. FastAPI 저장소 PR 머지
4. 웹 저장소에서 FastAPI 서브모듈 포인터 갱신
5. 웹 저장소에서 Django `.dockerignore` 보강
6. 웹 저장소에서 Django 이미지 빌드 및 테스트 수행

## 검증 방법

### 1. 컨텍스트 추출 검증

이 검증은 실제 `COPY . .` 또는 현재 Docker 컨텍스트에 어떤 파일이 들어가는지 확인하는 데 유용하다.

### Django

```bash
dest=$(mktemp -d)
docker buildx build --output type=local,dest="$dest" -f- services/django <<'EOF'
FROM scratch
COPY . /
EOF

find "$dest" -maxdepth 3 -type f | sort
test ! -f "$dest/chat/tests.py"
test ! -f "$dest/orders/tests.py"
test ! -f "$dest/pets/tests.py"
test ! -f "$dest/users/tests.py"
test ! -f "$dest/config/test_settings.py"
```

### FastAPI

FastAPI 저장소 루트 기준:

```bash
dest=$(mktemp -d)
docker buildx build --output type=local,dest="$dest" -f- . <<'EOF'
FROM scratch
COPY . /
EOF

find "$dest" -maxdepth 4 -type f | sort
test ! -d "$dest/docs"
test ! -d "$dest/test"
test ! -d "$dest/before"
test ! -d "$dest/deploy"
test ! -d "$dest/.github"
test ! -e "$dest/.test-deploy/.env"
```

### 2. 실제 이미지 빌드 검증

### Django

```bash
docker compose -f deploy/local/docker-compose.yml build django
docker compose -f deploy/local/docker-compose.yml run --rm django python manage.py test
```

### FastAPI

FastAPI 저장소 루트 기준:

```bash
docker build -t tailtalk-fastapi:ci .
docker run --rm tailtalk-fastapi:ci python -m compileall main.py final_ai
docker run --rm tailtalk-fastapi:ci python -c "from main import app; print(app.title)"
docker run --rm tailtalk-fastapi:ci python -c "from fastapi.testclient import TestClient; import main; client = TestClient(main.app); resp = client.get('/health'); assert resp.status_code == 200, resp.text"
docker run --rm tailtalk-fastapi:ci sh -lc 'test ! -d /app/docs && test ! -d /app/test && test ! -d /app/before'
```

## 변경 시 주의할 점

### 1. `.dockerignore`는 배포 번들 zip 생성과는 별개다

FastAPI의 `deploy/eb/test-fastapi/docker-compose.yml` 같은 파일은 이미지 안에는 필요 없지만,
CI에서 배포 번들을 만들 때는 여전히 저장소 안에 존재해야 한다.

즉 아래는 동시에 성립할 수 있다.

- Docker 이미지에는 `deploy/`가 없어야 함
- Git 저장소에는 `deploy/`가 있어야 함

### 2. allowlist `COPY`는 런타임 누락 위험이 있다

명시적 `COPY`는 가장 깔끔하지만, 새 런타임 경로가 생기면 Dockerfile도 같이 수정해야 한다.

그래서 FastAPI는 아래처럼 보는 것이 맞다.

- 장점: 불필요 파일 유입을 구조적으로 차단
- 단점: 새 런타임 디렉터리 추가 시 Dockerfile 수정 필요

현재 FastAPI 구조는 런타임 경로가 비교적 명확해서 allowlist 방식이 잘 맞는다.

### 3. Django는 지나치게 강한 allowlist보다 `.dockerignore` 우선이 낫다

Django는 앱 디렉터리가 더 분산되어 있고, 이후 앱이 추가될 가능성도 있어서
지금 당장은 `.dockerignore` 보강만으로도 충분히 개선 효과를 얻을 수 있다.

## 최종 권장안 요약

### FastAPI

- 반드시 수정
- 권장 조합:
  - `.dockerignore` 강화
  - `COPY . .` 제거
  - `COPY main.py`, `COPY final_ai`, `COPY scripts`로 변경
  - CI에 "불필요 파일 미포함" 검증 추가

### Django

- 이번에 같이 정리 권장
- 권장 조합:
  - `.dockerignore`에 `**/.env`, `Dockerfile`, `**/tests.py`, `config/test_settings.py` 추가
  - Dockerfile은 우선 유지

## 실제 수정 파일 목록

웹 저장소 기준:

- `docs/infra/10_docker_image_context_hardening.md`
- `services/django/.dockerignore`
- 필요 시 `services/django/Dockerfile`

FastAPI 서브모듈 저장소 기준:

- `services/fastapi/.dockerignore`
- `services/fastapi/Dockerfile`
- `services/fastapi/.github/workflows/ci-cd.yml`

## 추천 PR 분리

PR은 아래처럼 나누는 편이 안전하다.

1. FastAPI 저장소 PR
   - 이미지 컨텍스트 정리
   - Dockerfile allowlist 전환
   - CI 이미지 내용 검증 추가
2. 웹 저장소 PR
   - FastAPI 서브모듈 포인터 업데이트
   - Django `.dockerignore` 정리

이렇게 나누면 서브모듈 규칙도 지키고, 배포 영향 범위도 더 명확하게 관리할 수 있다.

## 적용 완료 기준

아래 조건이 만족되면 이번 정리는 완료로 봐도 된다.

- FastAPI 이미지 안에 `docs/`, `test/`, `before/`, `deploy/`, `.github/`, `.test-deploy/.env`가 없다.
- FastAPI 이미지가 기존처럼 `main.py` import와 `/health` 응답에 성공한다.
- Django 이미지 안에 `chat/tests.py`, `orders/tests.py`, `pets/tests.py`, `users/tests.py`, `config/test_settings.py`, `Dockerfile`이 없다.
- Django 이미지가 기존처럼 `manage.py test`와 앱 기동에 성공한다.
