# Elastic Beanstalk 환경변수 입력 가이드

## 목적

이 문서는 테스트 Elastic Beanstalk 환경에서 프로젝트 실행에 필요한 환경변수를 어디에 넣어야 하는지, AWS 콘솔에서 어떻게 입력하는지, Django/FastAPI 각각 어떤 키가 필요한지를 정리한 문서이다.

대상 환경:

- Django: `test-tailtalk-django-env`
- FastAPI: `test-tailtalk-fastapi-env`
- AWS Region: `ap-northeast-2`

## 핵심 원칙

이 프로젝트에서 실제 실행 설정값의 원천은 로컬 `.env` 파일이 아니라 Elastic Beanstalk 환경변수다.

정리하면:

- 로컬 개발: 각 서비스의 로컬 `.env` 또는 셸 환경변수 사용
- EB 배포: AWS Elastic Beanstalk `Environment properties` 사용
- 배포 번들: 애플리케이션 설정값을 담는 곳이 아니라, 배포에 필요한 파일만 담는 곳

현재 테스트 EB 배포 구조 기준 핵심 파일:

- `.github/workflows/ci-cd.yml`
- `deploy/eb/test-django/docker-compose.yml`
- `services/fastapi/.github/workflows/ci-cd.yml`
- `services/fastapi/deploy/eb/test-fastapi/docker-compose.yml`

권장 구조는 아래와 같다.

1. EB 배포 번들에는 앱 비밀값이 들어 있는 `.env` 파일을 넣지 않는다.
2. EB 환경 속성(`Environment properties`)에 값을 저장한다.
3. 배포 시 EB가 제공하는 `.env` 값을 Docker Compose 변수 치환에 사용하고, 배포 compose에 명시한 키만 컨테이너에 전달한다.

AWS 공식 문서도 Elastic Beanstalk 환경변수를 `Environment properties`에서 관리하도록 안내한다.

- Environment properties: <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environments-cfg-softwaresettings.html>
- Running environment configuration changes: <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environment-configuration-methods-after.html>

## 왜 EB 환경변수로 넣어야 하는가

이 프로젝트에서 필요한 값 중 상당수는 비밀값 또는 환경 의존 값이다.

예:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `INTERNAL_SERVICE_TOKEN`
- `GOOGLE_CLIENT_SECRET`
- `OPENAI_API_KEY`

이 값들을 저장소나 배포 zip에 넣으면 관리가 어렵고 유출 위험이 커진다. 따라서 AWS Console 또는 AWS CLI를 통해 EB 환경에 저장하는 편이 맞다.

## AWS 콘솔에서 입력하는 방법

아래 절차는 AWS 공식 문서의 Elastic Beanstalk 콘솔 흐름을 기준으로 작성했다.

### 1. AWS 콘솔 접속

1. AWS Management Console에 로그인한다.
2. 우측 상단 Region이 `Asia Pacific (Seoul) / ap-northeast-2`인지 확인한다.
3. 서비스 검색에서 `Elastic Beanstalk`를 연다.

### 2. 대상 환경 선택

1. 왼쪽에서 `Environments`를 선택한다.
2. 아래 중 하나를 클릭한다.
   - Django: `test-tailtalk-django-env`
   - FastAPI: `test-tailtalk-fastapi-env`

### 3. Environment properties 편집 화면으로 이동

1. 환경 상세 페이지에서 `Configuration`으로 이동한다.
2. `Updates, monitoring, and logging` 카드에서 `Edit`를 누른다.
3. 페이지 아래쪽의 `Environment properties` 섹션으로 내려간다.

참고:

- 콘솔 UI 문구는 시점에 따라 약간 바뀔 수 있지만, `Configuration` 안의 `Environment properties` 편집 화면으로 들어가면 된다.

### 4. 키와 값 입력

1. `Environment properties`에서 한 줄에 하나씩 `Key`와 `Value`를 입력한다.
2. 새 항목을 추가할 때는 `Add environment property`를 사용한다.
3. 이미 존재하는 키는 해당 줄의 값을 수정한다.

입력 예시:

```text
Key: GOOGLE_CLIENT_ID
Value: 발급받은 OAuth client id
```

```text
Key: OPENAI_API_KEY
Value: 실제 OpenAI API key
```

### 5. 적용

1. 입력을 마쳤으면 화면 하단의 `Apply`를 누른다.
2. Elastic Beanstalk가 환경 업데이트를 시작한다.
3. 몇 분 후 상태가 `Ready`이고 Health가 `Green`인지 확인한다.

주의:

- 값을 저장하면 컨테이너가 재시작될 수 있다.
- 오타가 있으면 앱이 바로 기동 실패할 수 있으니 키 이름을 정확히 맞춘다.

### 6. 적용 후 확인

입력 후에는 아래 항목을 확인하는 편이 좋다.

- Django 홈: `/`
- Django 헬스 체크: `/health/`
- FastAPI 홈: `/`
- FastAPI 헬스 체크: `/health`
- OAuth 시작 URL: `/auth/google/start/`, `/auth/naver/start/`, `/auth/kakao/start/`

## 환경별 키 정리

아래 목록은 현재 코드와 테스트 EB 환경을 기준으로 정리했다.

## Django 환경

대상 환경:

- `test-tailtalk-django-env`

코드 기준 참조 위치:

- `services/django/config/settings.py`

### 이미 등록되어 있는 핵심 키

값은 문서에 적지 않지만, 현재 테스트 Django EB에는 아래 키들이 이미 등록되어 있다.

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `FASTAPI_INTERNAL_CHAT_URL`
- `INTERNAL_SERVICE_TOKEN`
- `CORS_ALLOWED_ORIGINS`

### 지금 추가 입력이 필요한 키

소셜 로그인과 외부 URL 구성을 위해 아래 키를 입력해야 한다.

- `APP_BASE_URL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `KAKAO_CLIENT_ID`
- `KAKAO_CLIENT_SECRET`

### 선택적으로 입력할 수 있는 키

아래 키는 기능이나 운영 정책에 따라 넣는다.

- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SESSION_COOKIE_SECURE`
- `DJANGO_CSRF_COOKIE_SECURE`
- `SOCIAL_AUTH_REQUESTS_TIMEOUT`

주의:

- 현재 테스트 EB 배포 compose에는 `AWS_S3_*`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `USE_SQLITE`, `SQLITE_NAME`를 전달하지 않는다.
- 위 값들은 현재 코드의 테스트 EB 배포 경로에서는 사용하지 않는다.

### `APP_BASE_URL` 입력 기준

`APP_BASE_URL`은 OAuth 콜백 URL과 외부 절대 URL 생성에 사용된다.

테스트 EB 기본 URL을 그대로 쓸 경우 예시는 아래와 같다.

```text
http://test-tailtalk-django-env.eba-idn3t8gh.ap-northeast-2.elasticbeanstalk.com
```

주의:

- OAuth provider가 HTTPS redirect URI를 요구하면, EB 기본 HTTP URL 대신 SSL이 붙은 도메인을 사용해야 한다.
- 그 경우 `APP_BASE_URL`도 반드시 같은 HTTPS 도메인으로 맞춘다.

### OAuth callback URL 예시

`APP_BASE_URL`이 위 테스트 URL이라면 callback URL 예시는 아래와 같다.

```text
http://test-tailtalk-django-env.eba-idn3t8gh.ap-northeast-2.elasticbeanstalk.com/auth/google/callback/
http://test-tailtalk-django-env.eba-idn3t8gh.ap-northeast-2.elasticbeanstalk.com/auth/naver/callback/
http://test-tailtalk-django-env.eba-idn3t8gh.ap-northeast-2.elasticbeanstalk.com/auth/kakao/callback/
```

위 URL은 AWS Console에 넣는 값이 아니라, Google/Naver/Kakao 개발자 콘솔에 등록해야 하는 redirect URI다.

## FastAPI 환경

대상 환경:

- `test-tailtalk-fastapi-env`

코드 기준 참조 위치:

- `services/fastapi/deploy/eb/test-fastapi/docker-compose.yml`
- `services/fastapi/final_ai/core/config.py`
- `services/fastapi/final_ai/pipeline/utils.py`

### 이미 등록되어 있는 키

현재 테스트 FastAPI EB에는 아래 키들이 등록되어 있다.

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `OPENAI_API_KEY`

### 지금 점검 또는 교체가 필요한 키

- `OPENAI_API_KEY`

현재 테스트 환경에는 이 키가 존재하지만, 실제 서비스 호출에 쓸 값인지 반드시 확인하고 필요하면 교체해야 한다.

### LangSmith 추적을 켜려면 추가할 키

LangSmith에서 FastAPI 답변 생성 흐름을 추적하려면 아래 키를 `test-tailtalk-fastapi-env`의
`Environment properties`에 추가한다.

- `LANGSMITH_TRACING`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`
- `LANGSMITH_ENDPOINT`
- `LANGSMITH_WORKSPACE_ID`

권장 예시는 아래와 같다.

```text
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=tailtalk-fastapi
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

설명:

- `LANGSMITH_API_KEY`: LangSmith API key
- `LANGSMITH_PROJECT`: 트레이스를 모아볼 프로젝트 이름
- `LANGSMITH_WORKSPACE_ID`: 여러 workspace를 쓰는 경우에만 필요
- `LANGSMITH_ENDPOINT`: 기본 SaaS를 쓰면 보통 `https://api.smith.langchain.com`

주의:

- 현재 FastAPI 테스트 EB 배포 compose는 `POSTGRES_*`, `OPENAI_API_KEY`, `LANGSMITH_*`를 컨테이너에 전달한다.
- 즉 레거시 벡터 DB 관련 키, `INTERNAL_SERVICE_TOKEN`, `LLM_MODEL`은 현재 테스트 EB 배포 경로에서 사용하지 않는다.

## 레거시 키 메모

이전 배포 흐름에서는 배포 zip 내부 `.env`에 아래 키를 넣어 사용했다.

- `DJANGO_IMAGE`
- `FASTAPI_IMAGE`

이 값들은 이미지 태그 전달용이었다. 배포 번들에 앱 설정용 `.env`를 넣지 않는 구조로 정리하면, 앱 비밀값과는 분리해서 관리하는 것이 맞다.

## 입력 실수 방지 체크리스트

값을 넣기 전에 아래를 확인한다.

1. 키 이름 오타가 없는지 확인한다.
2. `APP_BASE_URL`과 OAuth provider 콘솔의 redirect URI가 서로 일치하는지 확인한다.
3. `OPENAI_API_KEY`는 테스트용 문자열이 아니라 실제 사용 가능한 키인지 확인한다.
4. `POSTGRES_*` 값이 현재 FastAPI 런타임이 접근 가능한 PostgreSQL을 가리키는지 확인한다.
5. HTTPS가 필요한 provider를 쓰는 경우 SSL 도메인이 준비되어 있는지 확인한다.

## 운영 팁

- 비밀값은 문서나 저장소에 적지 말고 AWS Console 또는 AWS CLI에서만 관리한다.
- 값을 바꾼 뒤에는 환경 상태가 `Ready / Green`으로 돌아올 때까지 기다린다.
- OAuth는 환경변수만 넣는다고 끝나지 않고, provider 콘솔 redirect URI 등록까지 맞아야 정상 동작한다.

## 참고 문서

- AWS Elastic Beanstalk environment properties: <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environments-cfg-softwaresettings.html>
- AWS Elastic Beanstalk configuration updates after environment creation: <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environment-configuration-methods-after.html>
