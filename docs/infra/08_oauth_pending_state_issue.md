# OAuth 임시 상태 관리 이슈 정리

작성일: 2026-03-18  
브랜치: `auth-api`

## 1. 문제 현상

현재 소셜 로그인 흐름에서 아래 문제가 발생한다.

1. 사용자가 하나의 OAuth provider로 인증한다.
2. `/profile/?setup=1` 로 이동한다.
3. 회원정보 입력을 끝내지 않고 브라우저 뒤로가기를 누른다.
4. OAuth 인증 페이지가 다시 보이거나, 다른 provider 인증을 다시 시도할 수 있다.
5. 이후 다른 provider로 인증하면 프로필 페이지의 계정 관리 영역에 여러 provider 연동 내역이 누적되어 보인다.

즉, "회원정보 입력 완료 전" 상태인데도 OAuth 연동 정보가 이미 확정 저장되고 있다.

## 2. 원인 분석

이 문제의 핵심은 프론트 캐시가 아니라 백엔드 상태 관리 방식이다.

현재 구조는 MVT + Django 세션 로그인 기반이고, OAuth callback 성공 시점에 이미 아래 작업을 끝내고 있다.

- `User` 생성 또는 조회
- `UserProfile` 생성 또는 갱신
- `SocialAccount` 생성
- `login(request, user)` 수행

이 때문에 사용자가 프로필 입력을 끝내지 않아도 provider 연동이 확정된다.

## 3. 현재 코드에서 원인이 되는 위치

### 3.1 callback 처리

파일:

- [page_views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/page_views.py)

문제 지점:

- `social_login_callback_view`

현재 callback 성공 시 바로:

- provider token 교환
- 사용자 조회/생성
- 소셜 계정 저장
- 세션 로그인
- `/profile/?setup=1` 이동

까지 처리한다.

즉, 프로필 페이지는 "추가 입력 단계"처럼 보이지만, 실제로는 이미 서버 측 로그인과 provider 연동이 완료된 뒤다.

### 3.2 사용자/소셜 계정 생성 로직

파일:

- [views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/views.py)

문제 지점:

- `get_or_create_social_user(profile)`

이 함수는 callback 성공 직후 아래를 즉시 DB에 반영한다.

- `User`
- `UserProfile`
- `SocialAccount`

따라서 사용자가 회원정보 입력을 마무리하지 않아도 provider 연결 상태가 남는다.

### 3.3 프로필 페이지

파일:

- [profile.html](/home/playdata/SKN22-Final-2Team-WEB/services/django/templates/users/profile.html)

현재 역할:

- 이미 로그인된 사용자 정보 편집
- 이미 생성된 `SocialAccount` 상태 표시

즉, 이 페이지는 "임시 회원가입 완료 전 단계"가 아니라 "확정된 사용자 설정 페이지"로 동작하고 있다.

## 4. 왜 프론트만 수정해서는 해결되지 않는가

브라우저 뒤로가기나 캐시 문제처럼 보이지만, 본질은 서버에 이미 저장된 상태다.

프론트에서 다음을 해도 근본 해결은 어렵다.

- 뒤로가기 막기
- 캐시 무효화
- 버튼 비활성화
- 히스토리 제어

이유:

- 이미 DB에 `SocialAccount`가 저장됨
- 이미 세션 로그인 완료됨
- 다시 진입하면 서버가 "이미 로그인된 사용자"로 인식함

즉, 프론트는 보조 대응만 가능하고 근본 수정은 백엔드에서 해야 한다.

## 5. 권장 수정 방향

권장 방식은 "OAuth 성공 즉시 확정 저장"이 아니라 "임시 OAuth 상태 보관 후 최종 입력 시 확정 저장" 구조로 바꾸는 것이다.

### 권장 흐름

1. OAuth callback 성공
2. provider 프로필 정보만 세션에 임시 저장
3. 아직 `SocialAccount`는 DB에 저장하지 않음
4. 아직 최종 사용자 확정도 하지 않음
5. `/profile/?setup=1` 또는 별도 onboarding 페이지 이동
6. 사용자가 추가 정보 입력 후 저장
7. 이 시점에만 `User`, `UserProfile`, `SocialAccount` 확정
8. 저장 완료 후 정상 로그인 완료 처리

### 사용자가 이탈하는 경우

- 취소
- 로그아웃
- 다른 provider 재시도
- 회원정보 입력 완료 전 페이지 이탈

이 경우 세션에 저장된 임시 OAuth 상태를 폐기한다.

## 6. 필요한 백엔드 변경 포인트

### 6.1 callback 뷰 수정

파일:

- [page_views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/page_views.py)

해야 할 일:

- callback에서 바로 `login(request, user)` 하지 않기
- callback에서 바로 `SocialAccount` 저장하지 않기
- provider에서 받은 프로필 데이터를 세션에 `pending_oauth` 형태로 저장

예시 세션 구조:

```python
request.session["pending_oauth"] = {
    "provider": "kakao",
    "provider_user_id": "...",
    "email": "...",
    "nickname": "...",
    "profile_image_url": "...",
    "extra_data": {...},
}
```

### 6.2 확정 저장 로직 분리

파일:

- [views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/views.py)

해야 할 일:

- `get_or_create_social_user()`를 "즉시 저장용"과 "확정 저장용"으로 분리하거나
- 최종 프로필 제출 시점에만 이 함수를 호출하도록 변경

### 6.3 프로필 저장 시 확정 처리

파일:

- [page_views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/page_views.py)
- [profile.html](/home/playdata/SKN22-Final-2Team-WEB/services/django/templates/users/profile.html)

해야 할 일:

- `setup=1` 상태에서 저장 버튼 클릭 시
- 세션의 `pending_oauth`를 읽어서
- 그때 `User`, `UserProfile`, `SocialAccount`를 확정 저장
- 저장 성공 후에만 로그인 완료 처리

### 6.4 이탈 시 pending 상태 삭제

백엔드에서 최소한 아래 시점엔 세션의 `pending_oauth`를 비워야 한다.

- 취소 버튼 클릭
- 로그아웃
- 다른 provider 로그인 시작
- 프로필 저장 완료
- 오류 발생 후 로그인 페이지 복귀

## 7. 프론트/MVT에서 보조적으로 할 수 있는 수정

프론트 또는 템플릿(JS)에서 할 수 있는 보조 대응:

- 프로필 페이지 취소 버튼을 누르면 pending OAuth 삭제 endpoint 호출
- 브라우저 뒤로가기 시 stale 화면을 새로고침
- OAuth 완료 후 캐시 방지 헤더 또는 no-store 적용
- 다른 provider 버튼 클릭 전 pending 상태 확인

하지만 이건 보조 수단이다.  
핵심 해결책은 서버에서 확정 저장 시점을 뒤로 미루는 것이다.

## 8. 결론

이 문제는 프론트 캐시 이슈처럼 보이지만, 실제로는 백엔드에서 OAuth 연동을 너무 일찍 확정하고 있기 때문에 발생한다.

근본 수정 우선순위:

1. 백엔드 callback 처리 방식 변경
2. `SocialAccount` 저장 시점을 프로필 완료 후로 이동
3. pending OAuth 세션 상태 도입
4. 이탈 시 pending 상태 삭제

먼저 손봐야 할 파일:

- [page_views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/page_views.py)
- [views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/views.py)
- [profile.html](/home/playdata/SKN22-Final-2Team-WEB/services/django/templates/users/profile.html)
