# 개발 협업 컨벤션

> **프로젝트**: SKN22 Final Project · 2팀
> **작성일**: 2026-03-06

---

## 1. Git 브랜치 전략

| 브랜치 | 용도 |
|---|---|
| `main` | 배포 가능한 안정 코드. 직접 push 금지. |
| `develop` | 통합 개발 브랜치. PR 머지 대상. |
| `feature/<이슈번호>-<설명>` | 기능 개발. 예: `feature/42-chat-session` |
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

```markdown
## 변경 사항
<!-- 무엇을 왜 변경했는지 -->

## 관련 이슈
closes #이슈번호

## 테스트
- [ ] 로컬 테스트 완료
- [ ] 관련 테스트 코드 작성

## 리뷰 요청 사항
<!-- 리뷰어가 집중해서 봐야 할 부분 -->
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

## 5. 기술 스택 문서화

> 상세 기술 스택은 `requirements_spec_v1.md` 섹션 4-1 참고.

각 기술 선택 근거는 멘토링 전 팀 내 합의 후 해당 섹션에 추가 기재.

- TBD 항목 (LLM 모델, sLLM 파인튜닝 여부) 은 멘토링 때 확정.
