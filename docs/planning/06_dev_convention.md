# 개발 협업 컨벤션

> **프로젝트**: SKN22 Final Project · 2팀
> **작성일**: 2026-03-06

---

## 1. Git 브랜치 전략

| 브랜치 | 용도 |
|---|---|
| `main` | 배포 가능한 안정 코드. 직접 push 금지. |
| `develop` | 통합 개발 브랜치. PR 머지 대상. |
| `feature/<이슈번호>-<설명>` | 서비스 기능 개발. 예: `feature/42-chat-session` |
| `data/<설명>` | 데이터 파이프라인, 크롤링, ETL, EDA. 예: `data/bronze-silver-pipeline` |
| `fix/<이슈번호>-<설명>` | 버그 수정. 예: `fix/55-cart-null-error` |
| `hotfix/<설명>` | main 긴급 수정. |

- 모든 작업은 `develop`에서 브랜치 생성 → PR → 머지
- PR은 이슈 관리자(또는 팀 리드) 승인 필수
- Conflict 발생 시 브랜치 작성자가 `develop` 최신화 후 해결

---

## 2. 커밋 메시지 컨벤션

```
<type>(<scope>): <subject>

[선택] body

[선택] footer
```

### type

| type | 설명 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서 변경 |
| `style` | 코드 포맷 (로직 변경 없음) |
| `refactor` | 리팩토링 |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, 설정, 패키지 변경 |
| `data` | 데이터 파이프라인, 크롤링 |

### 예시

```
feat(chat): 채팅 세션 생성 API 구현
fix(auth): JWT 만료 토큰 갱신 오류 수정
data(crawl): Playwright 어바웃펫 상품 수집 스크립트 추가
```

---

## 3. PR 컨벤션

### PR 제목

```
[<type>] <설명> (#이슈번호)
예: [feat] 펫 프로필 등록 API (#23)
```

### PR 템플릿

> `.github/pull_request_template.md` 에 등록되어 PR 생성 시 자동으로 표시된다.

```markdown
## 요약
<!-- 변경 사항을 한두 줄로 요약 -->

## 변경 사항
<!-- 무엇을 왜 변경했는지 bullet로 기술 -->

## 관련 이슈
<!-- 완전 해결: closes #번호 / 부분 관련: ref #번호 -->

## 체크리스트
- [ ] 변경 사항이 의도한 대로 동작함을 확인했다
- [ ] 관련 문서를 업데이트했다

## 리뷰 요청 사항
<!-- 리뷰어가 집중해서 봐야 할 부분 (없으면 삭제) -->
```

---

## 4. 코드 컨벤션

### Python (Django / FastAPI)

| 항목 | 설정 |
|---|---|
| 스타일 가이드 | PEP 8 |
| Formatter | `black` |
| Linter | `ruff` |
| Import 정렬 | `isort` |
| 타입 힌트 | 필수 (FastAPI는 Pydantic 모델 활용) |

### TypeScript / Next.js

| 항목 | 설정 |
|---|---|
| Formatter | `prettier` |
| Linter | `eslint` |
| 스타일 | camelCase (변수/함수), PascalCase (컴포넌트) |

### 공통

- 매직 넘버 금지 → 상수로 분리
- 함수/컴포넌트 단일 책임 원칙
- `.env` 파일 Git 커밋 금지 (`.gitignore` 필수)

---

## 5. 이슈 컨벤션

### 이슈 제목 형식

```
[prefix] 설명
```

| prefix 유형 | 예시 |
|---|---|
| 담당 영역 | `[frontend]`, `[backend]`, `[ai]`, `[infra]`, `[data]` |
| 평가 단계 (산출물) | `[기획]`, `[데이터 수집 및 저장]`, `[데이터 전처리]`, `[모델링 및 평가]`, `[모델 배포]`, `[발표 및 시연]` |

### 라벨 구성

> 상세: `planning/label_scheme.md`

이슈 등록 시 **Scope + Type** 조합 필수 라벨링.

| 유형 | 라벨 |
|---|---|
| Scope | `frontend` `backend` `ai` `infra` `data` |
| Type | `feat` `fix` `docs` `refactor` `test` `chore` |
| Status | `blocked` `wontfix` |
| Special | `artifact` (평가 산출물), `sprint` (현재 스프린트) |

**예시**: 챗봇 인터페이스 구현 이슈 → `frontend` + `feat`

### 마일스톤

| 마일스톤 | 기간 | 대상 주차 |
|---|---|---|
| 1. 기획/시스템설계 주간 | 1~2주차 | 설계·문서·환경 세팅 |
| 2. 구현 주간1 | 3~4주차 | 인증·프로필·파이프라인·챗봇 뼈대 |
| 3. 구현 주간2 | 5~6주차 | 추천·RAG·장바구니·기능 고도화 |
| 4. 테스트/발표 주간 | 7~8주차 | 어드민·CI/CD·QA·마무리 |

### 칸반 보드 Status

| Status | 설명 |
|---|---|
| Backlog | 등록되었으나 아직 시작 전 |
| Ready | 착수 가능 (선행 이슈 완료) |
| In Progress | 현재 작업 중 |
| In Review | PR 리뷰 중 |
| Done | 완료 |

- 이슈 등록 시 기본값: **Backlog**
- 작업 시작 시 직접 **In Progress** 로 이동

---

## 6. 기술 스택 문서화

> 상세 기술 스택은 `planning/03_requirements_spec.md` 섹션 2-1 참고.

각 기술 선택 근거는 멘토링 전 팀 내 합의 후 해당 섹션에 추가 기재.

- TBD 항목 (LLM 모델, sLLM 파인튜닝 여부) 은 멘토링 때 확정.
