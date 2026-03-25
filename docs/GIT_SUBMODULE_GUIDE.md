# Git Submodule 안내

## 변경 사항

`services/fastapi` 디렉토리가 **git submodule**로 변경되었습니다.

- **WEB 레포**: `SKN22-Final-2Team-WEB` (메인 프로젝트)
- **AI 레포**: `SKN22-Final-2Team-AI` (submodule, `services/fastapi`에 연결)

이제 AI 코드는 별도 저장소에서 독립적으로 관리되며, WEB 레포는 특정 커밋을 참조하는 방식으로 동작합니다.

---

## 1. 최초 설정

### A. 이미 WEB 레포를 클론한 경우

```bash
# 1) 최신 코드 pull
git pull origin develop

# 2) submodule 초기화 및 다운로드
git submodule init
git submodule update
```

> `git pull` 후 `services/fastapi` 폴더가 비어있다면 반드시 위 명령을 실행해야 합니다.

### B. 새로 클론하는 경우

```bash
# --recurse-submodules 옵션으로 한 번에 클론
git clone --recurse-submodules https://github.com/skn-ai22-251029/SKN22-Final-2Team-WEB
```

---

## 2. Submodule 최신 커밋 가져오기

AI 레포에 새로운 커밋이 push된 경우, WEB 레포에서 다음과 같이 업데이트합니다.

```bash
# 1) submodule 디렉토리로 이동해서 최신 코드 pull
cd services/fastapi
git pull origin develop

# 2) WEB 레포 루트로 돌아와서 변경된 참조 커밋을 기록
cd ../..
git add services/fastapi
git commit -m "Update AI submodule to latest"
git push origin develop
```

또는 한 줄로 실행:

```bash
git submodule update --remote services/fastapi && git add services/fastapi && git commit -m "Update AI submodule to latest" && git push origin develop
```

---

## 3. 자주 발생하는 문제

### `services/fastapi` 폴더가 비어있어요

```bash
git submodule init
git submodule update
```

### pull 했는데 submodule이 자동 업데이트가 안 돼요

submodule은 `git pull`만으로 자동 업데이트되지 않습니다. pull 후 아래 명령을 추가로 실행하세요.

```bash
git submodule update
```

또는 pull할 때 항상 submodule도 함께 업데이트하려면:

```bash
git pull --recurse-submodules
```

### 매번 `--recurse-submodules` 치기 귀찮아요

아래 설정을 한 번만 해두면 `git pull` 시 자동으로 submodule도 업데이트됩니다.

```bash
git config submodule.recurse true
```
