# DBeaver로 Test RDS 확인하기

## 배경

테스트 Django EB 환경이 바라보는 RDS는 아래와 같다.

- EB 환경: `test-tailtalk-django-env`
- RDS endpoint: `test-tailtalk-postgres-v2.cpkmaq4eqdte.ap-northeast-2.rds.amazonaws.com`
- Engine: `PostgreSQL`
- `PubliclyAccessible=False`

즉, DBeaver에서 RDS endpoint로 직접 붙는 방식은 동작하지 않는다.
사용자 PC에서 `EC2(EB 인스턴스) -> RDS` SSH 터널을 열고, DBeaver는 `localhost`로 붙어야 한다.

## 준비물

- `aws` CLI
- `ssh`, `ssh-keygen`
- `curl`
- DBeaver

## 빠른 실행

프로젝트 루트에서 아래를 실행한다.

```bash
bash scripts/aws/start_test_rds_dbeaver_tunnel.sh
```

스크립트 동작:

1. EB 환경 변수에서 실제 RDS 접속 정보 조회
2. 현재 내 공인 IP 확인
3. EB 인스턴스 Security Group에 내 IP로 `22/tcp` 임시 허용
4. EC2 Instance Connect로 임시 SSH 키 업로드
5. 로컬 `127.0.0.1:15432` -> RDS `5432` 터널 오픈
6. 종료 시 임시 `22/tcp` 규칙 자동 제거

실행 중 터미널은 닫지 말아야 한다.

## DBeaver 입력값

스크립트가 시작되면 아래 값을 출력한다.

- Host: `127.0.0.1`
- Port: `15432`
- Database: `tailtalk`
- Username: `tailtalk`
- Password: 스크립트 출력값 사용

DB 타입은 `PostgreSQL`로 선택하면 된다.

## 자주 쓰는 옵션

```bash
# 터널은 열지 않고 접속 정보만 출력
PRINT_ONLY=1 bash scripts/aws/start_test_rds_dbeaver_tunnel.sh

# 로컬 포트 변경
LOCAL_PORT=25432 bash scripts/aws/start_test_rds_dbeaver_tunnel.sh

# 공인 IP 자동 감지가 안 될 때 직접 지정
PUBLIC_IP_CIDR=203.0.113.10/32 bash scripts/aws/start_test_rds_dbeaver_tunnel.sh

# 종료 후에도 22 허용 규칙 유지
KEEP_SSH_RULE=1 bash scripts/aws/start_test_rds_dbeaver_tunnel.sh
```

## 참고

- AWS 자격증명이 셸에 없으면 기본적으로 `services/django/.env`를 읽는다.
- DBeaver는 터널을 직접 여는 것이 아니라, 이미 열린 로컬 포트 `127.0.0.1:<LOCAL_PORT>` 에 접속한다.
- DBeaver 최초 PostgreSQL 연결 시 드라이버 다운로드가 필요할 수 있다.
