#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/services/django/.env}"

EB_APP_NAME="${EB_APP_NAME:-test-tailtalk-django}"
EB_ENV_NAME="${EB_ENV_NAME:-test-tailtalk-django-env}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-ap-northeast-2}"
EC2_OS_USER="${EC2_OS_USER:-ec2-user}"
LOCAL_PORT="${LOCAL_PORT:-15432}"
PRINT_ONLY="${PRINT_ONLY:-0}"
KEEP_SSH_RULE="${KEEP_SSH_RULE:-0}"
PUBLIC_IP_CIDR="${PUBLIC_IP_CIDR:-}"
EC2_SECURITY_GROUP_ID="${EC2_SECURITY_GROUP_ID:-}"

KEY_DIR=""
KEY_FILE=""
RULE_ADDED=0
SSH_GROUP_ID=""
CIDR=""

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: '$1' 명령을 찾을 수 없습니다." >&2
    exit 1
  }
}

require_value() {
  local name="$1"
  local value="$2"

  if [[ -z "$value" || "$value" == "None" ]]; then
    echo "ERROR: '$name' 값을 확인하지 못했습니다." >&2
    exit 1
  fi
}

load_aws_env() {
  if [[ -z "${AWS_ACCESS_KEY_ID:-}" || -z "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
    if [[ -f "$ENV_FILE" ]]; then
      set -a
      # shellcheck source=/dev/null
      source "$ENV_FILE"
      set +a
    fi
  fi

  : "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID 가 설정되어 있지 않습니다.}"
  : "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY 가 설정되어 있지 않습니다.}"

  export AWS_DEFAULT_REGION
}

eb_env_value() {
  local key="$1"

  aws elasticbeanstalk describe-configuration-settings \
    --application-name "$EB_APP_NAME" \
    --environment-name "$EB_ENV_NAME" \
    --query "ConfigurationSettings[0].OptionSettings[?Namespace=='aws:elasticbeanstalk:application:environment' && OptionName=='${key}'].Value | [0]" \
    --output text
}

resolve_instance_id() {
  aws elasticbeanstalk describe-environment-resources \
    --environment-name "$EB_ENV_NAME" \
    --query 'EnvironmentResources.Instances[0].Id' \
    --output text
}

resolve_instance_field() {
  local field="$1"

  aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query "Reservations[0].Instances[0].${field}" \
    --output text
}

resolve_ssh_group_id() {
  local group_ids
  local selected

  group_ids="$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].SecurityGroups[].GroupId' \
    --output text)"

  selected="$(aws ec2 describe-security-groups \
    --group-ids ${group_ids} \
    --query "SecurityGroups[?contains(GroupName, 'AWSEBSecurityGroup')].GroupId | [0]" \
    --output text)"

  if [[ -z "$selected" || "$selected" == "None" ]]; then
    selected="$(printf '%s\n' ${group_ids} | head -n1)"
  fi

  printf '%s\n' "$selected"
}

detect_public_ip_cidr() {
  if [[ -n "$PUBLIC_IP_CIDR" ]]; then
    printf '%s\n' "$PUBLIC_IP_CIDR"
    return 0
  fi

  need_cmd curl

  local ip
  ip="$(curl -fsS https://checkip.amazonaws.com | tr -d '[:space:]')"

  if [[ ! "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "ERROR: 공인 IP를 자동으로 확인하지 못했습니다. PUBLIC_IP_CIDR=x.x.x.x/32 로 지정하세요." >&2
    exit 1
  fi

  printf '%s/32\n' "$ip"
}

authorize_ssh_access() {
  local existing

  existing="$(aws ec2 describe-security-groups \
    --group-ids "$SSH_GROUP_ID" \
    --query "SecurityGroups[0].IpPermissions[?FromPort==\`22\` && ToPort==\`22\`].IpRanges[?CidrIp=='${CIDR}'].CidrIp | [0]" \
    --output text)"

  if [[ "$existing" == "$CIDR" ]]; then
    return 0
  fi

  aws ec2 authorize-security-group-ingress \
    --group-id "$SSH_GROUP_ID" \
    --ip-permissions "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=${CIDR},Description='tailtalk-rds-dbeaver-tunnel'}]" \
    >/dev/null

  RULE_ADDED=1
}

cleanup() {
  local exit_code=$?

  if [[ -n "$KEY_DIR" && -d "$KEY_DIR" ]]; then
    rm -rf "$KEY_DIR"
  fi

  if [[ "$RULE_ADDED" == "1" && "$KEEP_SSH_RULE" != "1" && -n "$SSH_GROUP_ID" && -n "$CIDR" ]]; then
    aws ec2 revoke-security-group-ingress \
      --group-id "$SSH_GROUP_ID" \
      --ip-permissions "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=${CIDR}}]" \
      >/dev/null || true
  fi

  exit "$exit_code"
}

print_summary() {
  cat <<EOF
[Tailtalk Test RDS]
- AWS region: ${AWS_DEFAULT_REGION}
- Elastic Beanstalk env: ${EB_ENV_NAME}
- EC2 instance: ${INSTANCE_ID}
- EC2 public IP: ${EC2_PUBLIC_IP}
- RDS endpoint: ${DB_HOST}:${DB_PORT}

[DBeaver 입력값]
- Host: 127.0.0.1
- Port: ${LOCAL_PORT}
- Database: ${DB_NAME}
- Username: ${DB_USER}
- Password: ${DB_PASSWORD}

터널이 열린 동안만 DBeaver에서 127.0.0.1:${LOCAL_PORT} 로 접속하면 됩니다.
종료하려면 이 터미널에서 Ctrl+C 를 누르세요.
EOF
}

main() {
  need_cmd aws
  need_cmd ssh
  need_cmd ssh-keygen

  load_aws_env

  DB_HOST="$(eb_env_value POSTGRES_HOST)"
  DB_PORT="$(eb_env_value POSTGRES_PORT)"
  DB_NAME="$(eb_env_value POSTGRES_DB)"
  DB_USER="$(eb_env_value POSTGRES_USER)"
  DB_PASSWORD="$(eb_env_value POSTGRES_PASSWORD)"
  INSTANCE_ID="$(resolve_instance_id)"

  require_value "POSTGRES_HOST" "$DB_HOST"
  require_value "POSTGRES_PORT" "$DB_PORT"
  require_value "POSTGRES_DB" "$DB_NAME"
  require_value "POSTGRES_USER" "$DB_USER"
  require_value "POSTGRES_PASSWORD" "$DB_PASSWORD"
  require_value "EC2 instance id" "$INSTANCE_ID"

  EC2_PUBLIC_IP="$(resolve_instance_field PublicIpAddress)"
  EC2_AZ="$(resolve_instance_field Placement.AvailabilityZone)"

  require_value "EC2 public IP" "$EC2_PUBLIC_IP"
  require_value "EC2 availability zone" "$EC2_AZ"

  SSH_GROUP_ID="${EC2_SECURITY_GROUP_ID:-$(resolve_ssh_group_id)}"
  require_value "EC2 security group" "$SSH_GROUP_ID"

  print_summary

  if [[ "$PRINT_ONLY" == "1" ]]; then
    exit 0
  fi

  CIDR="$(detect_public_ip_cidr)"
  authorize_ssh_access

  KEY_DIR="$(mktemp -d)"
  KEY_FILE="${KEY_DIR}/eb-tunnel-key"

  ssh-keygen -q -t rsa -b 2048 -N '' -f "$KEY_FILE"

  aws ec2-instance-connect send-ssh-public-key \
    --instance-id "$INSTANCE_ID" \
    --availability-zone "$EC2_AZ" \
    --instance-os-user "$EC2_OS_USER" \
    --ssh-public-key "file://${KEY_FILE}.pub" \
    >/dev/null

  echo
  echo "[Info] SSH 허용 CIDR: ${CIDR}"
  echo "[Info] 로컬 터널을 엽니다: 127.0.0.1:${LOCAL_PORT} -> ${DB_HOST}:${DB_PORT}"
  echo

  ssh \
    -N \
    -L "127.0.0.1:${LOCAL_PORT}:${DB_HOST}:${DB_PORT}" \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -o StrictHostKeyChecking=accept-new \
    -o IdentitiesOnly=yes \
    -i "$KEY_FILE" \
    "${EC2_OS_USER}@${EC2_PUBLIC_IP}"
}

trap cleanup EXIT INT TERM
main "$@"
