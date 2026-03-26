# Web/AI 분리 CI-CD 안정화 가이드

## 목적

이 문서는 `web` 저장소와 `AI` 저장소의 CI-CD를 완전히 분리한 뒤,

- `web` repo의 `develop` 대상 PR이 merge되어 closed 되면 Django만 배포되고
- `AI` repo의 `develop` 대상 PR이 merge되어 closed 되면 FastAPI만 배포되도록

문제 없이 운영하려면 무엇을 해야 하는지 정리한 실행 가이드다.

대상 저장소:

- Web upstream: `skn-ai22-251029/SKN22-Final-2Team-WEB`
- AI upstream: `skn-ai22-251029/SKN22-Final-2Team-AI`

대상 환경:

- Django EB: `test-tailtalk-django-env`
- FastAPI EB: `test-tailtalk-fastapi-env`
- Region: `ap-northeast-2`

## 목표 상태

최종적으로 원하는 동작은 아래와 같다.

### Web repo

- 트리거: `develop` 대상 PR merge 후 `closed`
- 실행 대상:
  - Django CI
  - Django Docker image build/push
  - Django EB deploy
- 비실행 대상:
  - FastAPI image build/push
  - FastAPI EB deploy
  - AI repo로부터의 cross-repo dispatch 기반 자동 연동

### AI repo

- 트리거: `develop` 대상 PR merge 후 `closed`
- 실행 대상:
  - FastAPI CI
  - FastAPI Docker image build/push
  - FastAPI EB deploy
- 비실행 대상:
  - Web repo PR 생성용 dispatch
  - Web repo deploy 연쇄 트리거

## 현재 확인한 사실

### 1. Web workflow는 분리 방향으로 수정돼 있다

현재 Web repo의 `.github/workflows/ci-cd.yml`은 Django만 배포하는 방향으로 바뀐 상태다.

핵심 변화:

- FastAPI deploy job 제거
- Django만 `deploy-django` 실행
- CI 빌드도 전체 스택이 아니라 `django` 서비스만 build

### 2. AI repo에는 FastAPI 전용 workflow가 추가돼 있다

현재 AI 서브모듈 안에는 `.github/workflows/ci-cd.yml`이 추가돼 있고,
별도 FastAPI deploy bundle 파일도 생긴 상태다.

관련 파일:

- `services/fastapi/.github/workflows/ci-cd.yml`
- `services/fastapi/deploy/eb/test-fastapi/docker-compose.yml`

### 3. 기존 cross-repo 연동 workflow는 목적에 따라 유지 여부를 결정한다

아래 workflow는 "FastAPI merge 후 Web repo submodule 포인터까지 연쇄 자동화"가 필요할 때 유지할 수 있다.

- Web repo: `.github/workflows/sync-fastapi-submodule.yml`
- AI repo: `services/fastapi/.github/workflows/notify-web-repo.yml`

이 둘을 유지하면, 배포는 분리하더라도 여전히 AI merge가 Web repo submodule sync PR 생성으로 이어진다.

즉 선택지는 두 가지다.

1. 배포만 완전히 분리하고 repo 간 자동 PR 생성도 끊는다
2. 배포는 분리하되, submodule 포인터 동기화 자동화는 유지한다

현재 저장소 운영이 두 번째에 가깝다면 이 workflow들은 삭제하면 안 된다.

## 실제 점검 결과

아래는 로컬에서 현재 workflow에 적힌 명령을 가능한 범위에서 그대로 재현한 결과다.

### Web 쪽

실행한 명령:

```bash
docker compose -f infra/docker-compose.yml build django
docker compose -f infra/docker-compose.yml run --rm django python manage.py test
```

결과:

- `build django`: 성공
- `python manage.py test`: 실패

실패 내용:

- 실패 테스트:
  - `users.tests.SocialLoginPageViewTests.test_social_login_callback_redirects_to_profile_and_stores_jwt`
- 기대값:
  - `/profile/?setup=1`
- 실제값:
  - `/chat/`

즉, 현재 상태로는 Web workflow의 `ci` job이 실패하므로 Django 자동 배포는 막힌다.

원인 파일:

- 테스트 기대값: `services/django/users/tests.py`
- 실제 구현: `services/django/users/page_views.py`

### AI 쪽

실행한 명령:

```bash
docker build -t tailtalk-fastapi:ci services/fastapi
docker run --rm tailtalk-fastapi:ci python -m compileall main.py final_ai
docker run --rm tailtalk-fastapi:ci python -c "import main; print(main.app.title)"
docker run --rm tailtalk-fastapi:ci python -c "from fastapi.testclient import TestClient; import main; client = TestClient(main.app); print(client.get('/health').status_code, client.get('/health').json())"
```

결과:

- Docker build: 성공
- `compileall`: 성공
- `import main`: 성공
- `/health` smoke test: `200 {'status': 'ok'}`

즉, 현재 코드 기준으로는 FastAPI image build와 기본 app startup은 가능하다.

다만 현재 AI workflow의 CI step은 `compileall`까지만 수행하므로,
미래의 import/runtime 회귀를 충분히 막지는 못한다.

## 문제 없이 돌리려면 반드시 해야 할 것

### 1. Web Django 테스트 실패를 먼저 정리

이 항목이 가장 우선이다.

지금 상태에서는 merge가 일어나도 Django CI가 실패해서 배포가 멈춘다.

선택지는 둘 중 하나다.

1. 구현을 테스트 기대값에 맞춘다.
   - 신규 소셜 로그인 사용자를 `/profile/?setup=1`로 보내도록 수정
2. 테스트를 현재 구현에 맞춘다.
   - 실제 정책이 `/chat/` 이동이라면 테스트 기대값을 `/chat/`로 수정

중요한 점:

- 이건 workflow 문제가 아니라 코드/테스트 불일치다.
- 어느 쪽이 제품 요구사항에 맞는지 먼저 결정해야 한다.

권장:

- 만약 "신규 소셜 사용자에게 프로필 보완 입력을 강제"가 요구사항이면 구현을 수정
- 그렇지 않고 바로 채팅 진입이 맞다면 테스트를 수정

### 2. AI workflow의 CI gate를 강화하고 deploy bundle까지 검증

현재 AI workflow는 단순 `docker build`와 `compileall`만으로는 부족하다.

```yaml
- docker build
- python -m compileall
```

이 조합은 문법 오류는 잡지만, 실제 app import나 라우팅 문제를 충분히 못 잡는다.

최소한 아래 수준으로 강화하는 것이 좋다.

#### 권장 smoke test

```yaml
- name: Build FastAPI image
  run: docker build -t tailtalk-fastapi:ci .

- name: Smoke test FastAPI app import
  run: docker run --rm tailtalk-fastapi:ci python -c "import main; print(main.app.title)"

- name: Smoke test FastAPI health endpoint
  run: docker run --rm tailtalk-fastapi:ci python -c "from fastapi.testclient import TestClient; import main; client = TestClient(main.app); resp = client.get('/health'); assert resp.status_code == 200, resp.text"
```

추가로 deploy bundle도 CI에서 한 번 렌더링하고 `docker compose config -q` 및 `/health` 기동 검증까지 해두는 편이 안전하다.

이렇게 해야 최소한 아래 종류의 문제를 배포 전에 막을 수 있다.

- import path 깨짐
- app object 생성 실패
- health route 등록 누락
- startup 직후 예외
- EB용 compose 경로 누락 또는 변수 치환 문제

### 3. Web workflow도 EB bundle 검증과 배포 후 health check를 포함해야 한다

Web repo는 Django 테스트만 통과한다고 끝내면 안 된다.

최소한 아래 검증이 들어가야 한다.

- `deploy/eb/test-django/nginx/nginx.conf`에 대한 `nginx -t`
- EB용 `docker-compose.yml` 렌더링 후 `docker compose config -q`
- 배포 완료 후 Elastic Beanstalk 환경 CNAME 조회
- `http://<cname>/health/` smoke test

이렇게 해야 로컬 테스트용 compose와 실제 EB bundle 사이의 차이 때문에 생기는 배포 사고를 줄일 수 있다.

### 4. 두 repo에 필요한 GitHub Secrets를 각각 등록

분리 전에는 Web repo 쪽에만 secret이 있어도 일부 흐름이 가능했지만,
분리 후에는 두 repo가 각자 자기 secret을 가져야 한다.

#### Web repo 필수 secrets

- `DJANGO_SECRET_KEY`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

#### AI repo 필수 secrets

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

주의:

- FastAPI는 runtime DB/OpenAI 설정을 EB 환경변수에서 받으므로,
  GitHub Actions secret에 `POSTGRES_*`, `OPENAI_API_KEY`를 꼭 넣어야 하는 구조는 아니다.
- 대신 EB `Environment properties`에 값이 정확히 들어 있어야 한다.

### 5. FastAPI deploy bundle을 AI repo 소유로 고정

분리 구조에서는 FastAPI EB 배포 정의 파일도 AI repo 쪽에 있어야 한다.

현재 web repo에서는 아래 서브모듈 경로가 곧 AI repo root 기준 배포 파일이다.

- `services/fastapi/deploy/eb/test-fastapi/docker-compose.yml`

이 파일은 AI repo에 커밋되어야 실제 GitHub Actions에서 사용할 수 있다.

중요:

- 서브모듈 워크트리 안에서 수정한 것만으로는 upstream AI repo에 반영되지 않는다
- 반드시 AI repo 자체에 commit/push 해야 한다

### 6. Web repo와 AI repo의 소유 책임을 문서로 명확히 적기

분리 후에는 운영 기준이 아래처럼 바뀐다.

#### Web repo 책임

- Django 테스트
- Django image build/push
- Django EB deploy
- Web 기능 문서/정적 자산/템플릿 관리

#### AI repo 책임

- FastAPI 테스트/스모크 체크
- FastAPI image build/push
- FastAPI EB deploy
- AI/RAG 관련 배포 자산 관리

#### 더 이상 자동으로 기대하면 안 되는 것

- AI merge 후 Web submodule 포인터 자동 반영
- Web repo 기준으로 FastAPI 최신 커밋이 항상 맞춰져 있다는 가정

## 권장 롤아웃 순서

아래 순서대로 진행하는 것이 가장 안전하다.

1. Django social login redirect 요구사항 확정
2. Django 코드 또는 테스트 수정
3. Web workflow에서 Django CI가 실제로 통과하는지 로컬/Actions에서 확인
4. AI workflow의 `compileall`을 import/health smoke test로 강화
5. AI repo에 필요한 secrets 등록
6. Web repo에 필요한 secrets 재점검
7. 기존 cross-repo workflow 삭제
8. AI repo에서 PR merge 한 번
9. FastAPI EB 자동 배포 결과 확인
10. Web repo에서 PR merge 한 번
11. Django EB 자동 배포 결과 확인

## 최종 점검 체크리스트

### Web merge 후

- GitHub Actions `ci` 성공
- GitHub Actions `deploy-django` 성공
- Docker Hub에 Django 새 태그 push 확인
- EB `test-tailtalk-django-env` 상태 `Ready / Green`
- Django `/health/` 정상 응답
- 로그인/프로필/채팅 페이지 핵심 동선 확인

### AI merge 후

- GitHub Actions `ci` 성공
- GitHub Actions `deploy-fastapi` 성공
- Docker Hub에 FastAPI 새 태그 push 확인
- EB `test-tailtalk-fastapi-env` 상태 `Ready / Green`
- FastAPI `/health` 정상 응답
- Django -> FastAPI 프록시 경로(`/api/chat/`) 기본 동작 확인

## 로컬 확인용 명령 모음

### Web repo

```bash
docker compose -f infra/docker-compose.yml build django
docker compose -f infra/docker-compose.yml run --rm django python manage.py test
```

### AI repo

```bash
docker build -t tailtalk-fastapi:ci services/fastapi
docker run --rm tailtalk-fastapi:ci python -c "import main; print(main.app.title)"
docker run --rm tailtalk-fastapi:ci python -c "from fastapi.testclient import TestClient; import main; client = TestClient(main.app); resp = client.get('/health'); print(resp.status_code, resp.json())"
```

## 롤백 기준

아래 상황이면 즉시 롤백 또는 배포 중단이 맞다.

- Web Django 테스트가 다시 실패
- AI smoke test가 실패
- EB 환경이 `Red` 또는 `Severe`
- Django는 떴지만 FastAPI 프록시 호출이 실패
- FastAPI는 떴지만 `/health`가 실패

롤백 방법:

1. 마지막 정상 이미지 태그 확인
2. EB application version을 마지막 정상 태그로 재배포
3. 원인 수정 후 다시 merge

## 한 줄 결론

현재 분리 방향 자체는 맞다.

하지만 "문제 없이" 돌리려면 최소한 아래 4가지는 끝내야 한다.

1. Django social login 테스트 실패 해결
2. AI workflow smoke test 강화
3. 기존 cross-repo sync workflow 제거
4. 두 repo에 필요한 secrets 각각 등록
