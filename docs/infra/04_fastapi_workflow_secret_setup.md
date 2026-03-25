# FastAPI 워크플로 시크릿 설정 가이드

## 목적

이 문서는 `services/fastapi/.github/workflows/notify-web-repo.yml` 워크플로가 정상 동작하도록, 어떤 토큰을 어디서 발급하고 어느 저장소에 등록해야 하는지 정리한 문서이다.

현재 기준으로는 `classic PAT` 사용을 기준으로 설명한다.

현재 전제:

- AI 저장소는 public 저장소
- Web upstream 저장소는 `skn-ai22-251029/SKN22-Final-2Team-WEB`
- AI 저장소에서 `develop` 브랜치 대상 PR이 merge되어 closed 되면
- AI 저장소 워크플로가 Web upstream 저장소로 `repository_dispatch` 이벤트를 보냄
- Web upstream 저장소가 이 이벤트를 받아 `services/fastapi` 서브모듈 포인터 업데이트 PR을 생성함

## 전체 흐름

1. AI 저장소에서 `develop` 대상 PR이 merge되어 closed 됨
2. AI 저장소 워크플로 `notify-web-repo.yml` 실행
3. AI 저장소에 저장된 시크릿 `WEB_REPO_DISPATCH_TOKEN`으로 Web upstream 저장소 GitHub API 호출
4. Web upstream 저장소에서 `fastapi-updated` 이벤트 수신
5. Web upstream 저장소 워크플로 `sync-fastapi-submodule.yml` 실행
6. Web upstream 저장소가 `services/fastapi` 서브모듈 포인터 변경 PR 생성

## 필요한 시크릿

현재 구조에서 추가로 필요한 시크릿은 하나뿐이다.

- 이름: `WEB_REPO_DISPATCH_TOKEN`
- 등록 위치: AI 저장소 GitHub Actions Secrets
- 용도: AI 저장소가 Web upstream 저장소로 `repository_dispatch` 이벤트를 보내기 위한 인증

## 왜 이 토큰이 필요한가

AI 저장소 워크플로는 아래 API를 호출한다.

```text
POST https://api.github.com/repos/skn-ai22-251029/SKN22-Final-2Team-WEB/dispatches
```

이 호출은 AI 저장소 내부 작업이 아니라, 다른 저장소인 Web upstream 저장소에 이벤트를 보내는 작업이다.

기본 `GITHUB_TOKEN`은 일반적으로 현재 실행 중인 저장소 범위 안에서만 동작하므로, 다른 저장소에 `repository_dispatch`를 보내는 용도로 쓰기 어렵다.

그래서 Web upstream 저장소에 접근 가능한 별도 토큰을 AI 저장소 시크릿으로 넣어야 한다.

## 어떤 토큰을 발급해야 하는가

현재 상황에서는 `classic PAT`를 사용하는 것이 가장 현실적이다.

권장 토큰 종류:

- Personal access token (classic)

이유:

- upstream 저장소가 fine-grained token의 `Only select repositories` 목록에 보이지 않을 수 있음
- `repository_dispatch` 호출을 빠르게 구성하기에 classic PAT가 단순함
- 현재 목적은 AI 저장소에서 Web upstream 저장소로 이벤트를 보내는 것임

## 토큰 발급 방법

### 1. GitHub에서 classic PAT 발급 페이지로 이동

GitHub 웹에서 아래 순서로 이동한다.

1. 우측 상단 프로필 클릭
2. `Settings`
3. 왼쪽 메뉴 하단 `Developer settings`
4. `Personal access tokens`
5. `Tokens (classic)`
6. `Generate new token`

### 2. 토큰 기본 정보 입력

예시:

- Token name: `ai-to-web-dispatch-classic`
- Expiration: 적절한 기간 선택

### 3. Scope 설정

최소한 아래 scope를 체크한다.

- `repo`

이 scope를 주면 Web upstream 저장소에 `repository_dispatch`를 보내는 용도로 가장 덜 애매하게 동작한다.

### 4. 토큰 생성 후 값 복사

토큰은 생성 직후 한 번만 전체 값을 볼 수 있다.

반드시 생성 직후 복사해서 안전한 곳에 보관해야 한다.

## 토큰을 어디에 넣어야 하는가

이 토큰은 Web upstream 저장소가 아니라 AI 저장소에 넣어야 한다.

등록 위치:

1. AI 저장소 GitHub 페이지로 이동
2. `Settings`
3. 왼쪽 메뉴 `Secrets and variables`
4. `Actions`
5. `New repository secret`

입력값:

- Name: `WEB_REPO_DISPATCH_TOKEN`
- Secret: 방금 발급한 토큰 값

## AI 저장소 워크플로에서 이 토큰을 어떻게 쓰는가

현재 AI 저장소에 추가한 워크플로 파일:

- `services/fastapi/.github/workflows/notify-web-repo.yml`

핵심 부분:

```yaml
env:
  WEB_REPO_DISPATCH_TOKEN: ${{ secrets.WEB_REPO_DISPATCH_TOKEN }}
```

이 값으로 아래 API를 호출한다.

```yaml
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${WEB_REPO_DISPATCH_TOKEN}" \
  https://api.github.com/repos/skn-ai22-251029/SKN22-Final-2Team-WEB/dispatches \
  -d '{
    "event_type": "fastapi-updated",
    "client_payload": {
      "branch": "develop",
      "sha": "'"${{ github.event.pull_request.merge_commit_sha }}"'"
    }
  }'
```

## Web upstream 저장소에는 어떤 시크릿이 필요한가

현재 기준으로는 별도 추가 시크릿이 꼭 필요하지 않다.

이유:

- AI 저장소는 public 저장소
- Web upstream 저장소 워크플로는 public AI 저장소를 읽어 서브모듈 최신 커밋을 가져올 수 있음
- Web upstream 저장소의 PR 생성은 기본 `github.token`으로 처리하도록 구성해 둠

즉, 현재 구조에서 새로 직접 등록해야 하는 시크릿은 AI 저장소의 `WEB_REPO_DISPATCH_TOKEN` 하나다.

## 실제 설정 후 확인 방법

### 1. AI 저장소 워크플로 파일이 커밋되어 있어야 함

AI 저장소에 아래 파일이 있어야 한다.

- `services/fastapi/.github/workflows/notify-web-repo.yml`

### 2. AI 저장소에 시크릿 등록

- `WEB_REPO_DISPATCH_TOKEN`

### 3. AI 저장소에서 `develop` 대상 PR merge

PR이 정상적으로 merge되어 closed 되면 AI 저장소 워크플로가 실행된다.

### 4. Web upstream 저장소 Actions 확인

Web upstream 저장소에서 아래 워크플로가 실행되는지 확인한다.

- `.github/workflows/sync-fastapi-submodule.yml`

### 5. Web upstream 저장소 PR 생성 확인

정상이라면 Web upstream 저장소에 아래 형태의 PR이 자동 생성된다.

- 브랜치: `bot/update-fastapi-submodule`
- 제목: `chore: update fastapi submodule to <sha>`

## 실패 시 점검 포인트

### 1. AI 저장소 시크릿 이름 오타

아래 이름이 정확히 일치해야 한다.

```text
WEB_REPO_DISPATCH_TOKEN
```

### 2. 토큰 권한 부족

Web upstream 저장소에 대한 권한이 너무 약하면 `repository_dispatch` 호출이 실패할 수 있다.

classic PAT 기준으로는 아래 scope가 가장 안전하다.

- `repo`

### 3. 조직 정책으로 classic PAT가 막혀 있음

조직에서 classic PAT 접근을 제한해두었다면 이 방식도 실패할 수 있다.

이 경우 조직 관리자 정책 확인이 필요하다.

### 4. AI 저장소 워크플로가 `develop`에 없거나 아직 푸시되지 않음

워크플로 파일이 로컬에만 있고 AI 저장소 원격에 반영되지 않았다면 동작하지 않는다.

### 5. Web upstream 저장소 워크플로 파일이 아직 반영되지 않음

Web upstream 저장소에도 아래 파일이 반영되어 있어야 한다.

- `.github/workflows/sync-fastapi-submodule.yml`

## 참고

fine-grained PAT도 원칙적으로 더 안전한 방식이지만, 현재처럼 upstream 저장소가 토큰 대상 목록에 보이지 않는 상황에서는 classic PAT가 더 현실적인 대안이다.

## 한 줄 정리

FastAPI 워크플로를 실제로 동작시키려면, GitHub에서 classic PAT를 발급하고 `repo` scope를 준 뒤 AI 저장소의 Actions Secret에 `WEB_REPO_DISPATCH_TOKEN` 이름으로 등록하면 된다.
