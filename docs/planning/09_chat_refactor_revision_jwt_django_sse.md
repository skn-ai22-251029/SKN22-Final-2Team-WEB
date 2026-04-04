# 채팅 리팩토링 수정판: Django JWT 인증 + FastAPI 내부 SSE 스트림

## 목적

이 문서는 [08_chat_question_flow_trace_refactor_plan.md](/home/playdata/SKN22-Final-2Team-WEB/docs/planning/08_chat_question_flow_trace_refactor_plan.md)의 수정판이다.

이번 수정판은 아래 전제를 명확히 둔다.

- 브라우저 사용자는 Django만 인증한다.
- Django가 JWT 인증, 세션 권한, 대화 저장의 유일한 경계다.
- FastAPI는 추가 사용자 인증 없이 내부 호출만 받아 LLM/검색을 수행하고 SSE 응답만 반환한다.
- 질문 1건 처리의 진실 공급원은 Django 세션과 Django 저장소다.
- FastAPI는 "상태 없는 내부 AI 실행기"에 가깝게 단순화한다.

---

## 1. 이 수정판이 기존 계획보다 나은 이유

기존 문서는 흐름 추적과 hotspot 식별은 정확하지만,
실행 계획상 아래 위험이 있었다.

- 가장 민감한 hot path를 먼저 쪼개면서도 회귀 테스트를 앞단에 고정하지 않았다.
- Django 쪽에 `application/` 계층을 새로 넣으려 해서 현재 저장소 관례와 어긋난다.
- SSE 최종 결과의 진실 공급원을 먼저 정하지 않아, 파일만 쪼개고 중복 책임이 남을 수 있다.
- FastAPI에서 LLM 호출과 도메인 정책 경계를 더 엄격히 나누는 방향이 계획에 충분히 반영되지 않았다.

따라서 이번 수정판은 아래 순서를 따른다.

1. 인증 경계와 SSE 계약을 먼저 고정한다.
2. 브라우저 -> Django -> FastAPI 스트림 구조를 먼저 단순화한다.
3. Django는 기존 `services / clients / selectors / dto / policies` 축을 유지한다.
4. FastAPI는 `api / application / domain / infrastructure` 경계를 더 선명하게 만든다.

---

## 2. 목표 아키텍처

### 2-1. 책임 경계

#### 브라우저

- 질문 입력
- Django SSE 응답 소비
- 토큰 단위 렌더링
- 추천상품 패널 갱신

#### Django

- JWT 인증
- 사용자/세션 권한 확인
- 사용자 메시지 저장
- FastAPI 내부 호출
- SSE 그대로 relay
- 최종 assistant 결과 저장
- 추천상품 저장

#### FastAPI

- 내부 요청 수신
- LLM 호출
- 추천/검색/도메인지식 조합
- SSE 응답 생성
- 사용자 인증 책임 없음

### 2-2. 인증 경계

핵심 원칙은 간단하다.

- 사용자 인증: Django만
- 내부 서비스 호출: Django -> FastAPI만
- FastAPI는 `Authorization: Bearer <user jwt>`를 해석하지 않음

FastAPI에 전달하는 값은 인증용이 아니라 추적용/문맥용이어야 한다.

- `X-Request-Id`
- `X-Session-Id`
- `X-User-Id`

즉 FastAPI는 "누가 로그인했는지 검증"하지 않고,
"Django가 검증해 준 사용자 문맥"만 받아 처리한다.

주의:

- 이 구조는 FastAPI가 외부 공개 엔드포인트가 아니라는 전제가 있어야 안전하다.
- FastAPI가 퍼블릭으로 열려 있다면 "추가 인증 없음"은 테스트 환경에서만 허용해야 한다.

---

## 3. SSE는 어떻게 세팅해야 하는가

## 3-1. 결론

이 구조에서는 **브라우저 -> Django는 `fetch()` 기반 스트리밍**,  
**Django -> FastAPI도 HTTP 스트리밍 relay**가 가장 현실적이다.

즉, `EventSource`보다 현재처럼 `POST + fetch + ReadableStream`이 맞다.

이유는 두 가지다.

1. 질문 전송은 body를 포함하는 `POST`가 자연스럽다.
2. JWT를 `Authorization` 헤더로 보낼 경우 `EventSource`는 커스텀 헤더를 붙일 수 없다.

따라서 브라우저가 JWT 헤더를 붙여 Django를 호출하는 구조라면,
`EventSource`는 사실상 선택지가 아니다.

## 3-2. 브라우저 -> Django SSE 설정

권장 방식:

- 메서드: `POST`
- 요청 URL: `/api/chat/sessions/{session_id}/messages/`
- 인증: Django JWT 검증
- 응답 타입: `text/event-stream`
- 클라이언트: `fetch()` + `ReadableStream`

권장 요청 헤더:

```http
Authorization: Bearer <jwt>
Content-Type: application/json
Accept: text/event-stream
```

권장 응답 헤더:

```http
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache, no-transform
Connection: keep-alive
X-Accel-Buffering: no
```

메모:

- Django가 JWT를 쿠키로만 받고, 브라우저도 `GET` 기반 구독만 한다면 `EventSource`를 검토할 수는 있다.
- 하지만 현재 채팅은 `POST body`가 필요하므로 `fetch` 스트림 유지가 맞다.

## 3-3. Django -> FastAPI SSE 설정

권장 방식:

- 메서드: `POST`
- 요청 URL: `/api/chat/stream`
  - 기존 `/api/chat/`를 유지해도 되지만 내부 스트림 endpoint 의도를 드러내려면 `/stream`이 더 명확하다.
- 인증: 없음
- 신뢰 방식: 내부 네트워크/VPC/프라이빗 서비스

권장 요청 헤더:

```http
Content-Type: application/json
Accept: text/event-stream
X-Request-Id: <uuid>
X-Session-Id: <django_session_id>
X-User-Id: <django_user_id>
```

권장 응답 헤더:

```http
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache, no-transform
Connection: keep-alive
X-Accel-Buffering: no
```

핵심은 Django가 FastAPI 응답을 **재가공하지 않고 최대한 그대로 relay** 하는 것이다.

---

## 4. SSE 이벤트 계약은 이렇게 잡는 게 좋다

## 4-1. 최소 권장 이벤트

현재 구조를 단순화하려면 아래 5개면 충분하다.

- `info`
- `token`
- `products`
- `final`
- `error`

그리고 스트림 종료 표시는 `done`으로 둔다.

즉 실제 계약은 아래 6개가 된다.

- `info`
- `token`
- `products`
- `final`
- `done`
- `error`

## 4-2. 왜 `final` 이벤트가 꼭 필요한가

현재 문제는 같은 응답을 세 군데에서 재조립한다는 점이다.

- FastAPI가 `response`를 token으로 쪼갬
- Django가 token을 다시 이어붙여 저장
- 브라우저가 token을 다시 이어붙여 렌더링

이 중복을 줄이려면 FastAPI가 마지막에 **완성된 정답**을 한 번 더 명시적으로 보내야 한다.

권장:

- `token`은 사용자 화면의 타이핑 효과용
- `final`은 저장/후처리/정합성 보장용

이렇게 하면 Django는 `token`을 저장용으로 재조립할 필요가 없다.

## 4-3. 권장 payload 형태

### `info`

```text
data: {"type":"info","request_id":"...","message":"추천을 준비하고 있습니다."}

```

### `token`

```text
data: {"type":"token","content":"초코에게 "}

```

### `products`

```text
data: {"type":"products","cards":[{"goods_id":"...","product_name":"..."}]}

```

### `final`

```text
data: {
  "type":"final",
  "message":"초코에게는 저알러지 사료를 먼저 추천합니다.",
  "cards":[{"goods_id":"...","product_name":"..."}],
  "meta":{"request_id":"...","session_id":"..."}
}

```

### `done`

```text
data: {"type":"done"}

```

### `error`

```text
data: {"type":"error","message":"응답 생성 중 오류가 발생했습니다."}

```

## 4-4. `event:` 필드는 꼭 필요한가

현재 프론트 구현 기준으로는 `event:` 필드 없이 `data:`만으로 충분하다.

즉 지금처럼 JSON 안에 `type`을 넣는 방식으로 유지해도 된다.

```text
data: {"type":"token","content":"..."}

```

이 방식이 좋은 이유:

- 현재 브라우저 코드와 바로 맞는다.
- Django relay도 단순하다.
- `fetch` 스트림으로 읽을 때 별도 event-name parser가 필요 없다.

즉 이 프로젝트에서는 아래가 더 적절하다.

- `event:` 라인 없음
- `data:` JSON 한 줄
- JSON 내부 `type`으로 분기

---

## 5. 이 구조에서 Django는 어떻게 저장해야 하는가

핵심 원칙:

- 사용자 메시지는 Django가 요청 직전에 저장
- assistant 메시지는 Django가 `final` 이벤트 기준으로 저장
- `token`은 저장 기준이 아니라 UI 표시 기준

즉 Django 저장 흐름은 아래가 맞다.

1. 사용자 메시지 저장
2. FastAPI 스트림 relay 시작
3. `products` 이벤트가 오면 메모리 상 임시 보관 가능
4. `final` 이벤트가 오면
   - assistant message 저장
   - recommendation 저장
   - session touch
5. `done`은 종료 확인 용도만 사용

이렇게 하면 Django는 더 이상 `token`을 이어붙여 저장용 text를 재구성하지 않아도 된다.

---

## 6. FastAPI는 어떤 책임까지만 가지는 게 맞는가

이 수정판의 핵심은 FastAPI를 "내부 추론 엔진"으로 좁히는 것이다.

FastAPI가 가져야 할 책임:

- 요청 payload 해석
- graph/orchestration 실행
- LLM 호출
- 추천 상품/도메인지식 조합
- SSE 이벤트 생성
- request_id/session_id/user_id 로그 남기기

FastAPI가 버려야 할 책임:

- 사용자 JWT 인증
- 세션 CRUD
- 대화 메시지 영속화
- 사용자 기록 저장

즉 FastAPI는 "답을 만들어 스트림으로 반환"까지만 책임진다.

---

## 7. 수정된 실행 순서

### Phase 0. 계약과 회귀 테스트 먼저 고정

가장 먼저 해야 할 일:

- Django 채팅 API 회귀 테스트
- FastAPI `/api/chat/` SSE 이벤트 순서 테스트
- `final` 이벤트 계약 테스트

이 단계 없이 hot path를 먼저 분해하면 회귀를 잡기 어렵다.

### Phase 1. SSE 계약 개편

우선 변경:

- FastAPI가 `final` 이벤트를 명시적으로 보냄
- Django는 `final` 이벤트 기준으로 assistant 저장
- 기존 token 재조립 저장 로직 제거

핵심 효과:

- Django 저장 책임 단순화
- 브라우저 표시와 저장 결과 불일치 감소

### Phase 2. Django relay / 저장 분리

새 파일 제안:

- `services/django/chat/services/chat_proxy_service.py`
- `services/django/chat/services/stream_capture_service.py`
- `services/django/chat/services/conversation_persistence_service.py`

주의:

- Django에는 새 `application/` 계층을 넣지 않는다.
- 현재 저장소 관례대로 `services/` 아래에서 분리한다.

### Phase 3. FastAPI 스트림 오케스트레이션 분리

새 파일 제안:

- `services/fastapi/final_ai/application/chat/stream_orchestrator.py`
- `services/fastapi/final_ai/application/chat/event_stream_service.py`

분리 목표:

- graph 실행
- disconnect/cancel 처리
- SSE 이벤트 시퀀스 생성

를 서로 다른 파일로 나눈다.

### Phase 4. intent / search / response 서비스 분해

우선순위:

1. `domain/intent/service.py`
2. `domain/recommendation/search_service.py`
3. `domain/response/compose_service.py`

기준:

- prompt builder 분리
- policy/helper 분리
- LLM 호출은 가능한 공통 adapter를 통해 실행

### Phase 5. FastAPI를 내부 서비스로 더 명확히 고정

이 단계에서 정리할 것:

- 외부 사용자 인증 제거
- 내부 추적 헤더만 유지
- 필요 시 internal-only network 또는 reverse proxy 제한 적용

---

## 8. 구현 시 주의할 점

### JWT 헤더를 쓴다면 `EventSource`로 바꾸지 않는다

이건 가장 중요한 판단 포인트다.

- `EventSource`는 커스텀 `Authorization` 헤더를 붙일 수 없다.
- 따라서 브라우저가 JWT를 헤더로 Django에 보내는 구조면 `fetch` 스트림을 유지해야 한다.

### Django는 FastAPI SSE를 가능한 그대로 relay 한다

좋은 구조:

- Django는 프레임을 유지한 채 relay
- 저장은 `final` 이벤트만 사용

나쁜 구조:

- Django가 token을 다시 이어붙여 assistant text를 복원
- Django가 FastAPI event를 자체 형식으로 재조립

### heartbeat를 넣는 게 좋다

LLM 응답이 길거나 검색이 오래 걸리면 중간에 idle timeout이 날 수 있다.

권장:

- FastAPI가 15~30초마다 heartbeat comment 또는 `info` 이벤트 전송

예:

```text
: keep-alive

```

또는

```text
data: {"type":"info","message":"still_processing"}

```

### 프록시 버퍼링을 반드시 끈다

Django, Nginx, ALB 앞단에서 버퍼링이 걸리면 SSE 의미가 없어진다.

최소 확인 항목:

- `Content-Type: text/event-stream`
- `X-Accel-Buffering: no`
- `Cache-Control: no-cache, no-transform`

---

## 9. 최종 권장안

현재 수정된 프로젝트 구조 기준으로 가장 권장하는 구조는 이렇다.

- 브라우저 -> Django
  - JWT 인증
  - `fetch POST` 스트리밍
- Django -> FastAPI
  - 내부 `POST` 스트림 호출
  - 인증 없음
  - `X-Request-Id`, `X-Session-Id`, `X-User-Id`만 전달
- FastAPI -> Django
  - `info`, `token`, `products`, `final`, `done`, `error` SSE
- Django 저장
  - `final` 이벤트 기준으로 assistant/recommendation 저장

즉 핵심은 두 가지다.

1. **인증은 Django에서 끝낸다**
2. **저장은 `token`이 아니라 `final` 기준으로 한다**

이 두 가지를 먼저 고정하면, 이후 리팩토링은 구조 정리로 내려가고 hot path 회귀 위험이 크게 줄어든다.
