# MVT OAuth 연동 변경사항 정리

작성일: 2026-03-18  
브랜치: `auth-api`

## 1. 배경

`origin/develop` 최신 반영 이후 프론트엔드 Next.js 앱은 제거되고, 화면은 Django MVT 템플릿으로 전환되었다.

따라서 기존의 "프론트 콜백 페이지에서 JWT 저장" 방식은 더 이상 현재 구조에 맞지 않는다.  
이번 변경은 Django MVT 기준으로 OAuth 로그인 흐름을 다시 구성한 내용이다.

## 2. 현재 구조

현재 로컬 개발 구조는 아래와 같다.

- 브라우저 진입점: Nginx `80` 포트
- 페이지 렌더링: Django MVT
- API: Django `/api/...`, FastAPI `/api/chat/...`, `/api/recommend/...`, `/api/products/...`

관련 설정:

- [nginx.conf](/home/playdata/SKN22-Final-2Team-WEB/infra/nginx/nginx.conf)
- [docker-compose.yml](/home/playdata/SKN22-Final-2Team-WEB/infra/docker-compose.yml)

현재 Nginx는 `/` 전체를 Django로 프록시하므로, MVT 페이지 접근 기준 URL은 `http://localhost`다.

## 3. 최종 OAuth 흐름

현재 구현된 OAuth 로그인 흐름은 아래와 같다.

1. 사용자가 `/login/` 또는 `/signup/` 페이지 진입
2. Google, Naver, Kakao 아이콘 클릭
3. 브라우저가 `/auth/<provider>/start/?remember=...` 요청
4. Django가 provider authorization URL 생성 후 외부 OAuth 페이지로 리다이렉트
5. provider 인증 성공 후 `/auth/<provider>/callback/` 으로 복귀
6. Django가 `code/state` 검증 및 provider 토큰 교환 수행
7. 로컬 `User`, `UserProfile`, `SocialAccount` 생성 또는 연결
8. Django 세션 로그인 수행
9. `/profile/?setup=1` 로 이동
10. 사용자가 추가 정보를 입력 후 저장

핵심 차이:

- 예전 프론트 방식: 브라우저에서 JWT 저장
- 현재 MVT 방식: 서버에서 `login(request, user)` 처리

## 4. 변경 파일

### 수정된 파일

- [page_urls.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/page_urls.py)
- [page_views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/page_views.py)
- [views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/views.py)
- [login.html](/home/playdata/SKN22-Final-2Team-WEB/services/django/templates/users/login.html)
- [signup.html](/home/playdata/SKN22-Final-2Team-WEB/services/django/templates/users/signup.html)
- [profile.html](/home/playdata/SKN22-Final-2Team-WEB/services/django/templates/users/profile.html)

## 5. 추가된 페이지 라우트

[page_urls.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/page_urls.py)에 아래 라우트를 추가했다.

- `/auth/<provider>/start/`
- `/auth/<provider>/callback/`

예시:

- `/auth/google/start/`
- `/auth/naver/start/`
- `/auth/kakao/start/`
- `/auth/google/callback/`
- `/auth/naver/callback/`
- `/auth/kakao/callback/`

## 6. start 뷰 동작

[page_views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/page_views.py)의 `social_login_start_view`는 아래 역할을 한다.

- provider별 redirect URI 생성
- `OAuthProviderClient.build_authorization_url()` 호출
- `state`를 세션에 저장
- remember 여부를 세션에 저장
- provider 로그인 페이지로 redirect

remember 파라미터:

- `?remember=on`
- `?remember=off`

로그인 템플릿에서는 체크박스 상태에 따라 이 값을 만들어 `/auth/<provider>/start/`로 이동한다.

## 7. callback 뷰 동작

[page_views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/page_views.py)의 `social_login_callback_view`는 아래 역할을 한다.

- `error` 파라미터 확인
- `code` 유무 확인
- provider/state 검증
- provider token 교환
- provider 사용자 정보 조회
- `get_or_create_social_user()` 호출
- `login(request, user)` 수행
- remember OFF면 세션 만료를 브라우저 세션 기준으로 설정
- `/profile/?setup=1` 로 redirect

즉, OAuth 성공 후 최종 이동 페이지는 `profile`이다.

## 8. 로그인/회원가입 템플릿 변경

### 로그인 페이지

[login.html](/home/playdata/SKN22-Final-2Team-WEB/services/django/templates/users/login.html) 변경점:

- 소셜 아이콘 링크를 실제 OAuth start URL로 변경
- remember 체크박스 상태에 따라 provider start URL에 `remember` 값 반영
- Django `messages` 출력 추가

### 회원가입 페이지

[signup.html](/home/playdata/SKN22-Final-2Team-WEB/services/django/templates/users/signup.html) 변경점:

- 소셜 가입 버튼도 동일하게 OAuth start URL로 연결
- `messages` 출력 추가

## 9. 프로필 페이지 변경

[profile.html](/home/playdata/SKN22-Final-2Team-WEB/services/django/templates/users/profile.html) 변경점:

- `?setup=1`일 때 안내 문구 표시
- 사용자가 OAuth 로그인 직후 추가 정보를 입력해야 함을 알림
- 현재 연결된 social account 상태를 provider별로 표시

표시 방식:

- 연결된 provider면 "연동 중"
- 없으면 "연동하기"

## 10. 사용자 생성 및 연결 방식

기존 DRF용 소셜 사용자 생성 로직을 공용 함수로 분리해 MVT에서도 재사용하도록 변경했다.

관련 함수:

- `get_or_create_social_user(profile)`
- `sync_social_profile(user, profile)`
- `build_fallback_email(provider, provider_user_id)`

위 함수는 [views.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/users/views.py)에 있다.

정책:

- 동일 provider + provider_user_id 있으면 기존 사용자 재사용
- 소셜 계정은 없지만 동일 이메일 유저가 있으면 연결
- 둘 다 없으면 새 사용자 생성
- 이메일이 없는 경우 fallback 이메일 생성

## 11. 로컬 테스트 환경에서 사용할 URL

현재 Docker Compose + Nginx 기준으로 브라우저에서 사용할 로컬 테스트 URL은 아래다.

기본 접속 URL:

- `http://localhost/`

로그인 페이지:

- `http://localhost/login/`

회원가입 페이지:

- `http://localhost/signup/`

프로필 페이지:

- `http://localhost/profile/`

OAuth 시작 URL 예시:

- `http://localhost/auth/google/start/?remember=on`
- `http://localhost/auth/naver/start/?remember=on`
- `http://localhost/auth/kakao/start/?remember=on`

중요:

- 현재 Compose 설정에서 외부에 열려 있는 포트는 Nginx `80`뿐이다
- Django `8000`은 `expose`만 되어 있고 외부 직접 접속용 `ports`는 없다
- 따라서 Docker 기준 로컬 테스트 URL은 `http://localhost`가 맞다

## 12. OAuth provider에 등록할 redirect URI

현재 구조에서 provider 개발자 콘솔에 등록해야 할 redirect URI는 아래 3개다.

- `http://localhost/auth/google/callback/`
- `http://localhost/auth/naver/callback/`
- `http://localhost/auth/kakao/callback/`

중요:

- trailing slash까지 정확히 맞춰 등록하는 편이 안전하다
- 현재 Django 라우트는 `/callback/` 형태다
- provider 콘솔 등록값과 실제 요청 redirect URI는 완전히 같아야 한다

## 13. OAuth 성공 후 실제 최종 이동 URL

사용자가 OAuth 인증에 성공한 뒤 provider가 보내는 URL은 우선 아래 callback URL이다.

예:

- `http://localhost/auth/google/callback/?code=...`

그 다음 Django 내부 처리 완료 후 사용자가 최종적으로 도착하는 URL은 아래다.

- `http://localhost/profile/?setup=1`

정리하면:

- provider redirect URI: `/auth/<provider>/callback/`
- 로그인 완료 후 최종 사용자 이동 URL: `/profile/?setup=1`

## 14. 검증 결과

실행한 검증:

- `python manage.py check`
- `python -m compileall services/django/users services/django/config`

결과:

- Django system check 통과
- Python 컴파일 통과

## 15. 참고 및 주의사항

- 로그인 상태 유지 여부는 Django 세션 만료 정책으로 제어한다
- 현재 구조는 JWT 저장 기반 SPA가 아니라 서버 세션 로그인 기반이다
- 운영 환경에서는 `http://localhost/...` 대신 실제 도메인 기준으로 redirect URI를 따로 등록해야 한다
- provider 콘솔에서 로컬 URL과 운영 URL을 각각 등록해야 할 수 있다
