# DBeaver RDS 재접속 런북

## 목적

이 문서는 한 번 종료했던 SSH 터널을 다시 열고,
Windows DBeaver에서 테스트 RDS를 다시 확인하는 절차를 정리한 문서다.

특히 `2026-03-27` 금요일에 실제로 사용했던 방식과 동일한 흐름으로 다시 붙는 것을 기준으로 작성했다.

## 현재 접속 구조

테스트 RDS는 private 이므로 DBeaver에서 RDS endpoint로 직접 붙지 않는다.
반드시 bastion EC2를 경유한 SSH 터널을 먼저 열어야 한다.

현재 확인된 대상:

- Bastion EC2 이름: `test-tailtalk-bastion`
- Bastion 공인 IP: `54.116.141.184`
- Bastion SSH 사용자: `ec2-user`
- Bastion 키 파일: `output/bastion/test-tailtalk-bastion-key.pem`
- RDS endpoint: `test-tailtalk-postgres-v2.cpkmaq4eqdte.ap-northeast-2.rds.amazonaws.com`
- RDS port: `5432`
- DBeaver 접속 대상: `127.0.0.1:15432`

즉 구조는 아래와 같다.

```text
DBeaver (Windows)
  -> 127.0.0.1:15432
  -> SSH 터널
  -> test-tailtalk-bastion (54.116.141.184)
  -> test-tailtalk-postgres-v2...:5432
```

## 지난 금요일에 실제로 썼던 방식

로컬 히스토리 기준으로 `2026-03-27`에 실제로 실행한 명령은 아래였다.

```bash
ssh -i /home/playdata/SKN22-Final-2Team-WEB/output/bastion/test-tailtalk-bastion-key.pem \
  -L 15432:test-tailtalk-postgres-v2.cpkmaq4eqdte.ap-northeast-2.rds.amazonaws.com:5432 \
  ec2-user@54.116.141.184
```

중요한 점:

- 그때도 `.pem` 키는 사용했다
- 다만 DBeaver 안에서 쓴 게 아니라 WSL/bash 쪽 SSH 터널에서 썼다
- DBeaver는 `127.0.0.1:15432` 로컬 포트만 보고 있었다

그래서 체감상 "DBeaver에서는 키를 안 썼다"처럼 느껴졌을 수 있다.

## 가장 권장하는 재접속 방법

기존과 가장 같은 방식은 Windows DBeaver는 그대로 두고,
WSL/bash에서 SSH 터널만 다시 여는 것이다.

### 1. WSL 터미널 열기

Ubuntu 또는 현재 작업 중인 WSL/bash 터미널을 연다.

### 2. 저장소 루트로 이동

```bash
cd /home/playdata/SKN22-Final-2Team-WEB
```

### 3. 기존 15432 포트가 이미 사용 중인지 확인

```bash
lsof -i :15432
```

아무것도 안 나오면 다음 단계로 간다.

프로세스가 보이면 이미 다른 SSH 터널이 떠 있거나,
이전 터널이 정리되지 않은 상태다.

### 4. SSH 터널 다시 열기

이제 아래 명령을 실행한다.

```bash
ssh -N -i /home/playdata/SKN22-Final-2Team-WEB/output/bastion/test-tailtalk-bastion-key.pem \
  -L 15432:test-tailtalk-postgres-v2.cpkmaq4eqdte.ap-northeast-2.rds.amazonaws.com:5432 \
  ec2-user@54.116.141.184
```

설명:

- `-N`: 쉘 접속 없이 포트포워딩만 유지
- `-i`: `.pem` 키 파일 지정
- `-L 15432:...:5432`: 내 PC `15432`를 RDS `5432`에 연결

이 명령은 성공하면 조용히 멈춰 있는 것처럼 보일 수 있다.
그 상태가 정상이다.

이 창은 닫지 말고 그대로 유지해야 한다.

### 5. DBeaver 열기

Windows DBeaver를 연다.

이미 저장된 연결이 있다.

- `TailTalk_RDS_PgPass`
- `tailtalk`

둘 다 현재 기준 `127.0.0.1:15432/tailtalk` 로 저장돼 있다.

가능하면 새 연결을 만들지 말고 기존 연결을 그대로 재사용한다.

### 6. 기존 연결로 접속

DBeaver에서 위 연결 중 하나를 더블클릭하거나 `Connect`를 누른다.

정상이라면 바로 붙는다.

## 새 연결을 다시 만들어야 할 때

기존 연결이 깨졌거나 새로 만들어야 하면 아래 값으로 만든다.

- DB 타입: `PostgreSQL`
- Host: `127.0.0.1`
- Port: `15432`
- Database: `tailtalk`

사용자명/비밀번호가 기억나지 않으면 새 문서에 하드코딩하지 말고,
프로젝트 루트에서 아래 명령으로 현재 값을 확인한다.

```bash
PRINT_ONLY=1 bash scripts/aws/start_test_rds_dbeaver_tunnel.sh
```

이 명령은 현재 AWS 기준 DB 접속 정보를 출력한다.

## PowerShell에서 다시 열고 싶을 때

지난 금요일의 실제 기록은 WSL/bash 방식이었다.
그래도 PowerShell에서 직접 열고 싶다면 아래 순서로 한다.

### 1. WSL 경로를 Windows 경로로 변환

WSL에서 아래를 실행하면 Windows에서 쓸 수 있는 경로가 나온다.

```bash
wslpath -w /home/playdata/SKN22-Final-2Team-WEB/output/bastion/test-tailtalk-bastion-key.pem
```

### 2. PowerShell에서 SSH 터널 열기

변환된 경로를 그대로 사용해서 실행한다.

```powershell
ssh -N -i "<wslpath -w 출력값>" `
  -L 15432:test-tailtalk-postgres-v2.cpkmaq4eqdte.ap-northeast-2.rds.amazonaws.com:5432 `
  ec2-user@54.116.141.184
```

PowerShell 방식은 키 경로나 권한 문제로 실패할 수 있다.
그럴 때는 WSL/bash 방식으로 여는 쪽이 더 안정적이다.

## 정상 연결 확인 방법

SSH 터널이 열린 상태에서 다른 터미널에서 아래를 확인한다.

WSL/bash:

```bash
lsof -i :15432
```

Windows PowerShell:

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 15432
```

정상이라면 DBeaver에서 `127.0.0.1:15432` 연결이 성공해야 한다.

## 자주 막히는 경우

### 1. `Connection timed out`

원인:

- Bastion EC2 보안그룹에 현재 공인 IP가 허용되지 않음

현재 확인된 SSH 허용 CIDR은 `222.112.208.66/32`다.
다른 네트워크에서 붙으면 timeout 이 날 수 있다.

### 2. `Permission denied (publickey)`

원인:

- 잘못된 `.pem` 파일 사용
- 사용자 계정을 `ec2-user`가 아닌 다른 값으로 사용

확인:

- 키 파일: `output/bastion/test-tailtalk-bastion-key.pem`
- 사용자: `ec2-user`

### 3. `Address already in use`

원인:

- `15432` 포트를 이미 다른 프로세스가 사용 중

확인:

```bash
lsof -i :15432
```

### 4. DBeaver에서 `Connection refused`

원인:

- SSH 터널 창을 닫았음
- SSH 터널이 애초에 성공하지 않았음

조치:

1. SSH 명령부터 다시 실행
2. 그 창을 닫지 않은 상태에서 DBeaver 접속

### 5. DBeaver가 사용자명/비밀번호를 다시 물어봄

원인:

- 기존 저장 연결이 초기화됐거나 새 연결을 만든 경우

조치:

```bash
PRINT_ONLY=1 bash scripts/aws/start_test_rds_dbeaver_tunnel.sh
```

로 현재 값을 확인해서 입력한다.

## 종료 방법

터널을 닫고 싶으면 SSH를 띄운 터미널에서 `Ctrl+C`를 누른다.

그 다음 DBeaver 연결은 더 이상 `127.0.0.1:15432`에 붙지 않는다.
다시 확인하려면 위 절차를 처음부터 반복하면 된다.
