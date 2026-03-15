# AWS IAM 설정 가이드

> 팀 공용 IAM User 기준 (EC2, S3 접근 권한 보유)

---

## 1. AWS CLI 자격증명 설정

IAM User의 Access Key를 팀원 각자 로컬에 설정.

```bash
aws configure
# AWS Access Key ID: <팀 공용 Access Key>
# AWS Secret Access Key: <팀 공용 Secret Key>
# Default region name: ap-northeast-2
# Default output format: json
```

> Access Key는 `.gitignore`에 등록된 `.env` 또는 `~/.aws/credentials`에만 보관. 절대 커밋 금지.

---

## 2. EC2 Instance Role 생성

> EC2 내부에서 S3에 접근할 때 Access Key 없이 Role로 처리.

1. AWS 콘솔 → IAM → Roles → **Create role**
2. Trusted entity: **AWS service → EC2**
3. Policy 연결: `AmazonS3FullAccess`
4. Role name: `skn22-ec2-role`
5. EC2 인스턴스에 연결
   - EC2 콘솔 → 인스턴스 선택 → Actions → Security → **Modify IAM role**

> Instance Role이 연결되면 EC2 내부 코드에서 Access Key 없이 S3 접근 가능.

---

## 3. EC2 SSH 접속 설정

팀원별 공개키를 EC2에 등록. 키 하나를 공유하지 않음.

```bash
# 팀원 로컬에서 키페어 생성
ssh-keygen -t ed25519 -C "teammate@skn22"

# 공개키 확인 후 팀장에게 전달
cat ~/.ssh/id_ed25519.pub
```

```bash
# EC2에서 등록
echo "ssh-ed25519 AAAA... teammate@skn22" >> ~/.ssh/authorized_keys
```

---

## 4. 완료 조건 체크리스트

- [ ] 팀원 5인 로컬 `aws configure` 완료
- [ ] `skn22-ec2-role` 생성 및 EC2 인스턴스에 연결
- [ ] 팀원별 SSH 공개키 EC2 등록
