# Google, Kakao, Naver OAuth 키 발급 가이드

작성일: 2026-03-18

## 1. 문서 목적

이 문서는 TailTalk 백엔드에서 사용할 아래 3개 provider의 OAuth 자격증명을 발급받는 방법을 정리한다.

- Google
- Kakao
- Naver

여기서 발급받는 값은 사용자 계정의 아이디/비밀번호가 아니라, 우리 서비스가 각 provider와 OAuth 인증을 수행하기 위한 앱 자격증명이다.

대체로 아래 값을 확보해야 한다.

- `client_id`
- `client_secret`

프로젝트의 현재 환경변수 키는 아래와 같다.

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `KAKAO_CLIENT_ID`
- `KAKAO_CLIENT_SECRET`
- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`

## 2. 사전 준비

각 provider 공통으로 먼저 준비할 것:

- 서비스용 운영/개발 계정
- 프론트 콜백 URL
- 백엔드에서 사용할 redirect URI 목록

예시 redirect URI:

- `http://localhost:3000/auth/google/callback`
- `http://localhost:3000/auth/kakao/callback`
- `http://localhost:3000/auth/naver/callback`
- 운영 도메인 사용 시 `https://...`

주의:

- provider 콘솔에 등록한 redirect URI와 실제 요청에 사용하는 `redirect_uri`는 정확히 일치해야 한다
- 로컬과 운영 URL은 각각 따로 등록해야 하는 경우가 많다

## 3. Google OAuth Client ID 발급 방법

### 3.1 개요

Google은 Google Cloud Console에서 OAuth Client를 만든다. 최근 공식 문서 기준 메뉴는 `Google Auth platform` 아래의 `Branding`, `Audience`, `Data Access`, `Clients`로 정리되어 있다.

### 3.2 발급 절차

1. Google Cloud Console에 로그인한다.
2. 프로젝트를 선택하거나 새 프로젝트를 만든다.
3. `Google Auth platform`으로 이동한다.
4. 아직 설정 전이면 OAuth 동의 화면 설정을 먼저 진행한다.
5. `Branding`에서 앱 이름, 지원 이메일 등 기본 정보를 입력한다.
6. 필요하면 `Audience`에서 앱 유형과 테스트 사용자 정책을 설정한다.
7. `Clients`로 이동한다.
8. `Create Client`를 클릭한다.
9. `Application type`으로 `Web application`을 선택한다.
10. 이름을 입력한다.
11. 필요 시 `Authorized JavaScript origins`에 프론트 도메인을 등록한다.
12. `Authorized redirect URIs`에 콜백 URL을 등록한다.
13. `Create`를 눌러 생성한다.

### 3.3 발급 후 확인할 값

생성 후 다음 값을 확보한다.

- Client ID
- Client Secret

프로젝트 `.env` 매핑:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

### 3.4 Google에서 특히 주의할 점

- Google OAuth는 동의 화면 설정이 선행되어야 한다
- `redirect_uri`가 등록값과 다르면 인증 코드 발급이 실패한다
- 테스트 상태에서는 테스트 사용자 제한이 있을 수 있다
- 민감한 scope를 쓰면 추가 검토가 필요할 수 있다

### 3.5 TailTalk 기준 권장값

현재 백엔드는 기본적으로 로그인용 사용자 정보만 사용하므로 최소 범위로 시작하는 편이 낫다.

- `openid`
- `email`
- `profile`

### 3.6 공식 문서

- Google OAuth 동의 화면 설정: https://developers.google.com/workspace/guides/configure-oauth-consent
- Google OAuth 클라이언트 생성: https://developers.google.com/workspace/guides/create-credentials
- Google 웹 서버 OAuth 흐름: https://developers.google.com/identity/protocols/oauth2/web-server

## 4. Kakao OAuth 키 발급 방법

### 4.1 개요

Kakao는 Kakao Developers에서 앱을 만들고, 그 앱의 `REST API key`와 `Client secret`을 사용한다. 현재 우리 백엔드는 REST API 방식으로 Kakao 로그인 토큰 교환을 처리하므로 JavaScript key가 아니라 REST API key 기준으로 보면 된다.

### 4.2 발급 절차

1. Kakao Developers에 로그인한다.
2. `내 애플리케이션`에서 새 앱을 생성한다.
3. 앱 생성 후 앱 관리 페이지로 이동한다.
4. `Kakao Login`을 활성화한다.
5. `App > Platform key > REST API key` 영역으로 이동한다.
6. `REST API key` 값을 확인한다.
7. 같은 화면에서 `Redirect URI`를 등록한다.
8. `Client secret` 항목이 활성화되어 있는지 확인한다.
9. 필요 시 `Client secret` 값을 생성 또는 복사한다.
10. 동의 항목이 필요하면 `Kakao Login`의 consent 관련 설정도 맞춘다.

### 4.3 발급 후 확인할 값

TailTalk 백엔드 기준으로 필요한 값:

- Kakao REST API key
- Kakao Client secret

프로젝트 `.env` 매핑:

```env
KAKAO_CLIENT_ID=...
KAKAO_CLIENT_SECRET=...
```

주의:

- 우리 코드에서 `KAKAO_CLIENT_ID`는 Kakao의 일반적인 "앱 이름"이 아니라 `REST API key`를 넣는 자리다
- `client_secret` 사용이 기본 활성화되어 있을 수 있으므로, 토큰 발급 시 서버에서 같이 보내야 한다

### 4.4 Kakao에서 특히 주의할 점

- `Kakao Login`이 OFF면 로그인 요청 시 오류가 발생할 수 있다
- `Redirect URI` 미등록 또는 불일치 시 `KOE006` 오류가 날 수 있다
- REST API 호출에 JavaScript key가 아니라 REST API key를 써야 한다
- `Client secret`은 브라우저 노출 없이 백엔드에서만 사용해야 한다

### 4.5 TailTalk 기준 체크포인트

- 앱 생성
- Kakao Login ON
- Redirect URI 등록
- REST API key 확보
- Client secret 확보
- 이메일/프로필 닉네임/프로필 이미지 consent 항목 확인

### 4.6 공식 문서

- Kakao Login 사전 준비: https://developers.kakao.com/docs/latest/en/kakaologin/prerequisite
- Kakao Login REST API: https://developers.kakao.com/docs/latest/en/kakaologin/rest-api
- Kakao 앱 설정 및 REST API key/Redirect URI/Client secret: https://developers.kakao.com/docs/latest/en/app-setting/app
- Kakao 보안 가이드: https://developers.kakao.com/docs/latest/en/getting-started/security-guideline

## 5. Naver OAuth Client ID/Secret 발급 방법

### 5.1 개요

Naver는 NAVER Developers에서 애플리케이션을 등록하고 `Client ID`, `Client Secret`을 발급받는다. 네이버 로그인 방식은 callback URL과 `state` 사용이 중요하다.

### 5.2 발급 절차

1. NAVER Developers에 로그인한다.
2. `Application > 애플리케이션 등록`으로 이동한다.
3. 애플리케이션 이름, 서비스 환경 등의 기본 정보를 입력한다.
4. 로그인 방식 오픈 API 사용 설정을 한다.
5. Callback URL을 등록한다.
6. 앱 등록을 완료한다.
7. `내 애플리케이션`으로 이동한다.
8. 방금 만든 앱을 선택한다.
9. 개요 또는 애플리케이션 정보 영역에서 `Client ID`, `Client Secret`을 확인한다.
10. `API 설정` 또는 `API 권한관리`에서 필요한 권한이 체크되어 있는지 확인한다.

### 5.3 발급 후 확인할 값

프로젝트 `.env` 매핑:

```env
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

### 5.4 Naver에서 특히 주의할 점

- 네이버 로그인은 authorization 요청 시 `state`가 필수다
- callback URL이 등록값과 다르면 인증이 실패한다
- `API 권한관리`에서 필요한 권한을 체크하지 않으면 403이 날 수 있다
- 개발 상태에서는 테스터 ID 제한이 적용될 수 있다

### 5.5 TailTalk 기준 체크포인트

- 네이버 로그인 사용 설정
- callback URL 등록
- `Client ID`, `Client Secret` 확인
- 프로필/이메일 관련 권한 확인

### 5.6 공식 문서

- 네이버 로그인 개발가이드: https://developers.naver.com/docs/login/devguide/devguide.md
- 내 애플리케이션 관리: https://developers.naver.com/docs/common/openapiguide/appconf.md

## 6. 발급 후 우리 프로젝트에 넣는 위치

현재 Django 백엔드는 아래 환경변수를 읽는다.

파일:

- [settings.py](/home/playdata/SKN22-Final-2Team-WEB/services/django/config/settings.py)

예시:

```env
GOOGLE_CLIENT_ID=발급받은_구글_Client_ID
GOOGLE_CLIENT_SECRET=발급받은_구글_Client_Secret

KAKAO_CLIENT_ID=발급받은_카카오_REST_API_KEY
KAKAO_CLIENT_SECRET=발급받은_카카오_Client_Secret

NAVER_CLIENT_ID=발급받은_네이버_Client_ID
NAVER_CLIENT_SECRET=발급받은_네이버_Client_Secret
```

샘플 키 정의 위치:

- [.env.example](/home/playdata/SKN22-Final-2Team-WEB/infra/.env.example)

실제 적용은 보통 아래 중 하나다.

- 로컬 개발: `infra/.env`
- 운영 서버: CI/CD secret 또는 배포 환경 secret store

## 7. provider별 용어 대응표

헷갈리기 쉬운 용어를 정리하면 아래와 같다.

| Provider | 콘솔에서 보이는 이름 | 우리 `.env` 키 |
| --- | --- | --- |
| Google | Client ID | `GOOGLE_CLIENT_ID` |
| Google | Client Secret | `GOOGLE_CLIENT_SECRET` |
| Kakao | REST API key | `KAKAO_CLIENT_ID` |
| Kakao | Client secret | `KAKAO_CLIENT_SECRET` |
| Naver | Client ID | `NAVER_CLIENT_ID` |
| Naver | Client Secret | `NAVER_CLIENT_SECRET` |

중요:

- Kakao의 `KAKAO_CLIENT_ID`는 일반적인 의미의 "OAuth client id"처럼 쓰이지만, 실제 콘솔 용어는 `REST API key`다

## 8. 실무 주의사항

- 절대로 실제 키를 Git에 커밋하지 않는다
- 프론트 코드에 `client_secret`를 넣지 않는다
- Redirect URI는 로컬/운영 각각 정확히 등록한다
- provider 콘솔에서 팀 권한과 소유자 계정을 명확히 관리한다
- 테스트 앱과 운영 앱을 분리하는 편이 안전하다

## 9. 지금 바로 필요한 최소 체크리스트

1. Google Cloud에서 Web application OAuth Client 생성
2. Kakao Developers에서 앱 생성 후 REST API key와 Client secret 확보
3. NAVER Developers에서 앱 등록 후 Client ID/Secret 확보
4. 각 provider에 로컬/운영 redirect URI 등록
5. `infra/.env`에 값 입력
6. 프론트 콜백 URL과 백엔드 요청 `redirect_uri` 일치 여부 확인

## 10. 참고

이 문서는 2026-03-18 기준 공식 문서와 공식 개발자 포털 메뉴명을 바탕으로 정리했다. 각 provider 콘솔 UI는 이후 바뀔 수 있으므로, 메뉴명이 달라졌다면 위 공식 문서 링크를 우선 기준으로 본다.
