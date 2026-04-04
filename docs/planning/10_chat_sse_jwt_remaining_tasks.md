# Chat SSE/JWT 남은 작업

## 현재 상태

- Django가 채팅 API의 인증 경계를 맡고, FastAPI는 내부 SSE 응답 서비스로 동작한다.
- FastAPI SSE는 `info -> token -> products -> final -> done` 계약을 사용한다.
- Django는 `final` 이벤트를 assistant 최종 저장 기준으로 사용한다.
- 브라우저는 `token`으로 스트리밍 표시를 하고, `final`로 최종 텍스트를 확정한다.

## 남은 작업

### 1. 인증 정책 확정

- 현재는 `JWT 우선 + session fallback` 상태다.
- 최종 정책을 `JWT 전용`으로 고정할지 결정해야 한다.
- `JWT 전용`으로 갈 경우 `services/django/chat/policies/chat_access_policy.py`에서 session fallback 제거가 필요하다.

### 2. 실제 사용자 플로우 재검증

- 로그인 후 `/chat/` 진입
- 질문 1건 전송
- `token -> products -> final -> done` 흐름 확인
- Django DB에 assistant 메시지와 추천 상품이 `final` 기준으로 저장되는지 확인

### 3. 테스트 보강

- Django chat API의 JWT 전용 케이스 추가
- `final` 이벤트 누락/중복 상황 방어 테스트 추가
- 브라우저가 아닌 서버 측 저장 기준이 항상 `final`인지 회귀 테스트 추가

### 4. 토큰 전달 방식 재검토

- 현재 chat 페이지 JS가 access token을 사용해 Django chat API를 호출한다.
- 동작에는 문제 없지만, 장기적으로는 전달 범위를 더 줄일 수 있는지 검토가 필요하다.

## 권장 순서

1. 실제 로그인 사용자로 채팅 smoke test
2. 인증 정책을 `JWT 전용`으로 갈지 결정
3. 결정된 정책 기준으로 테스트 보강
4. 필요 시 토큰 전달 방식 개선
