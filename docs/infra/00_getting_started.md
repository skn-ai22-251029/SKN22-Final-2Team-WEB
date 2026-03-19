# 협업 온보딩 가이드

> TailTalk 프로젝트에 처음 합류한 팀원을 위한 협업 가이드

---

## 1. 레포지토리 설정

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

> 로컬 환경 구성 및 실행 방법: [01_local_setup.md](./01_local_setup.md)
> DB 데이터 복원: [02_data_restore.md](./02_data_restore.md)

---

## 2. 브랜치 전략

### 기본 규칙

- 모든 작업은 **이슈 번호로 브랜치**를 따서 시작
- `develop` 브랜치에 PR로 머지 (직접 push 금지)
- `main` 브랜치는 배포 전용 — 건드리지 않는다

### 브랜치 이름 규칙

```
feature/<이슈번호>-<설명>   # 새 기능
fix/<이슈번호>-<설명>       # 버그 수정
docs/<이슈번호>-<설명>      # 문서 작업
chore/<이슈번호>-<설명>     # 빌드/설정
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
# upstream 최신화 (GitHub에서 fork → Sync fork 먼저)
git checkout develop
git pull origin develop

# 브랜치 생성
git checkout -b feature/12-user-login

# 작업 후 커밋
git add .
git commit -m "feat(auth): add login API"

# fork에 push 후 GitHub에서 upstream/develop으로 PR 생성
git push origin feature/12-user-login
```

---

## 3. 커밋 메시지 형식

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

## 4. PR 스코프 기준

**Backend 스코프**
```
services/django/
├── config/              # settings, urls, wsgi
├── */models.py          # 데이터 모델
├── */page_views.py      # 뷰 로직 (인증, ORM 쿼리, 리다이렉트)
├── */page_urls.py       # URL 라우팅
├── */views.py           # DRF API
├── */urls.py            # DRF API 라우팅
├── */serializers.py     # DRF 직렬화
├── */migrations/        # DB 마이그레이션
└── requirements.txt
```

**Frontend 스코프**
```
services/django/
├── templates/           # HTML 템플릿
│   ├── base.html
│   ├── users/
│   ├── pets/
│   ├── chat/
│   └── orders/
└── static/              # CSS, JS, 이미지
    ├── css/
    └── js/
```

---

## 5. 역할별 작업 디렉토리

| 역할 | 작업 경로 |
|---|---|
| Django Backend (Auth/API) | `services/django/` |
| Django Frontend (Templates) | `services/django/templates/`, `services/django/static/` |
| FastAPI (챗봇/추천) | `services/fastapi/` |
| 인프라 공통 | `infra/` |

> 본인 담당 서비스 외 디렉토리는 되도록 건드리지 않는다.
> 공통 설정(`infra/docker-compose.yml`, `.env.example` 등) 변경 시 팀에 공유할 것.

---

## 6. CI/CD

### 흐름

```
[fork] feature/xxx
  │
  └─ PR → [upstream] develop     # CI 없음, 코드 리뷰로 검증
                │
                └─ PR → [upstream] main
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
               CI: Build & Test    (main 머지 시)
                                   CD: DockerHub push
                                       → EB 배포
```

### 트리거

| 이벤트 | 브랜치 | 실행 |
|---|---|---|
| `pull_request` | `main` | CI — Build & Test |
| `push` | `main` | CI → CD — DockerHub push → EB 배포 |

> fork에서는 CI/CD가 동작하지 않는다.

### 배포 주소

- http://tailtalk.ap-northeast-2.elasticbeanstalk.com
