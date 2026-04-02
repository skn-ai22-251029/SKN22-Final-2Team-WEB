#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/manual_eb_deploy.sh <django|fastapi> [options]

Options:
  --env-file PATH          Runtime env file to package into the EB bundle
  --profile NAME           AWS CLI profile to use
  --region NAME            AWS region (default: ap-northeast-2)
  --image-repo URI         Override ECR repository URI
  --application-name NAME  Override Elastic Beanstalk application name
  --environment-name NAME  Override Elastic Beanstalk environment name
  --tag TAG                Override image tag and version suffix
  --skip-deploy            Build, push, and bundle only
  --skip-healthcheck       Skip final HTTP health check
  --help                   Show this message

Examples:
  bash scripts/manual_eb_deploy.sh django --env-file deploy/env/test-django.env --profile tailtalk
  bash scripts/manual_eb_deploy.sh fastapi --env-file deploy/env/test-fastapi.env --skip-deploy
EOF
}

log() {
  printf '[manual-eb-deploy] %s\n' "$*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

aws_cmd() {
  if [[ -n "${aws_profile}" ]]; then
    aws --profile "$aws_profile" --region "$region" "$@"
  else
    aws --region "$region" "$@"
  fi
}

service="${1:-}"
if [[ "$service" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "$service" ]]; then
  usage
  exit 1
fi
shift

region="${AWS_REGION:-ap-northeast-2}"
aws_profile="${AWS_PROFILE:-}"
image_repo=""
application_name=""
environment_name=""
env_file=""
image_tag=""
skip_deploy=0
skip_healthcheck=0

case "$service" in
  django)
    source_dir="$repo_root/services/django"
    deploy_template_root="$repo_root/deploy/eb/test-django"
    compose_template="$deploy_template_root/docker-compose.yml"
    compose_placeholder="__DJANGO_IMAGE__"
    image_repo_default="027099020675.dkr.ecr.ap-northeast-2.amazonaws.com/test-tailtalk-django"
    application_name_default="test-tailtalk-django"
    environment_name_default="test-tailtalk-django-env"
    env_file_default="$repo_root/deploy/env/test-django.env"
    health_path="/health/"
    git_ref_dir="$repo_root"
    ;;
  fastapi)
    source_dir="$repo_root/services/fastapi"
    deploy_template_root="$repo_root/services/fastapi/deploy/eb/test-fastapi"
    compose_template="$deploy_template_root/docker-compose.yml"
    compose_placeholder="__FASTAPI_IMAGE__"
    image_repo_default="027099020675.dkr.ecr.ap-northeast-2.amazonaws.com/test-tailtalk-fastapi"
    application_name_default="test-tailtalk-fastapi"
    environment_name_default="test-tailtalk-fastapi-env"
    env_file_default="$repo_root/deploy/env/test-fastapi.env"
    health_path="/health"
    git_ref_dir="$repo_root/services/fastapi"
    ;;
  *)
    usage
    exit 1
    ;;
esac

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      env_file="$2"
      shift 2
      ;;
    --profile)
      aws_profile="$2"
      shift 2
      ;;
    --region)
      region="$2"
      shift 2
      ;;
    --image-repo)
      image_repo="$2"
      shift 2
      ;;
    --application-name)
      application_name="$2"
      shift 2
      ;;
    --environment-name)
      environment_name="$2"
      shift 2
      ;;
    --tag)
      image_tag="$2"
      shift 2
      ;;
    --skip-deploy)
      skip_deploy=1
      shift
      ;;
    --skip-healthcheck)
      skip_healthcheck=1
      shift
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage
      exit 1
      ;;
  esac
done

image_repo="${image_repo:-$image_repo_default}"
application_name="${application_name:-$application_name_default}"
environment_name="${environment_name:-$environment_name_default}"
env_file="${env_file:-$env_file_default}"

if [[ ! -f "$env_file" ]]; then
  printf 'Env file not found: %s\n' "$env_file" >&2
  printf 'Copy the matching example file under deploy/env/*.example first.\n' >&2
  exit 1
fi

require_cmd aws
require_cmd docker
require_cmd python3
require_cmd zip
if [[ "$skip_healthcheck" -eq 0 ]]; then
  require_cmd curl
fi

log "Checking AWS credentials"
aws_cmd sts get-caller-identity >/dev/null

source_sha="$(git -C "$git_ref_dir" rev-parse --short HEAD)"
timestamp="$(date -u +%Y%m%d%H%M%S)"
image_tag="${image_tag:-${source_sha}-${timestamp}}"
image_uri="${image_repo}:${image_tag}"
version_label="${service}-${image_tag}"
registry="${image_repo%%/*}"

staging_root="$repo_root/.local/manual-deploy/${service}"
bundle_dir="$staging_root/bundle"
bundle_zip="$staging_root/${service}-deploy-${image_tag}.zip"

log "Logging in to ECR: $registry"
aws_cmd ecr get-login-password | docker login --username AWS --password-stdin "$registry"

build_cmd=(docker build -t "${image_repo}:latest" -t "${image_uri}")
if [[ "$service" == "fastapi" ]]; then
  build_cmd+=(--build-arg "PREWARM_FASTEMBED=${PREWARM_FASTEMBED:-1}")
fi
build_cmd+=("$source_dir")

log "Building image: $image_uri"
"${build_cmd[@]}"

log "Pushing image tags"
docker push "${image_repo}:latest"
docker push "${image_uri}"

log "Preparing Elastic Beanstalk bundle"
rm -rf "$bundle_dir" "$bundle_zip"
mkdir -p "$bundle_dir"

python3 - "$compose_template" "$bundle_dir/docker-compose.yml" "$compose_placeholder" "$image_uri" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1]).read_text()
out = Path(sys.argv[2])
placeholder = sys.argv[3]
image = sys.argv[4]
out.write_text(src.replace(placeholder, image))
PY

cp "$env_file" "$bundle_dir/.env"

if [[ "$service" == "django" ]]; then
  cp -r "$deploy_template_root/nginx" "$bundle_dir/nginx"
  cp -r "$deploy_template_root/.ebextensions" "$bundle_dir/.ebextensions"
  cp -r "$deploy_template_root/.platform" "$bundle_dir/.platform"
else
  cp -r "$deploy_template_root/.platform" "$bundle_dir/.platform"
fi

docker compose -f "$bundle_dir/docker-compose.yml" --env-file "$bundle_dir/.env" config -q

(
  cd "$bundle_dir"
  if [[ "$service" == "django" ]]; then
    zip -rq "$bundle_zip" docker-compose.yml .env nginx .ebextensions .platform
  else
    zip -rq "$bundle_zip" docker-compose.yml .env .platform
  fi
)

log "Bundle created: $bundle_zip"

if [[ "$skip_deploy" -eq 1 ]]; then
  log "Skip deploy enabled"
  printf 'IMAGE_URI=%s\n' "$image_uri"
  printf 'BUNDLE_ZIP=%s\n' "$bundle_zip"
  exit 0
fi

log "Resolving Elastic Beanstalk storage bucket"
s3_bucket="$(aws_cmd elasticbeanstalk create-storage-location --query 'S3Bucket' --output text)"
s3_key="manual-deploy/${application_name}/${version_label}.zip"

log "Uploading bundle to s3://${s3_bucket}/${s3_key}"
aws_cmd s3 cp "$bundle_zip" "s3://${s3_bucket}/${s3_key}"

log "Creating application version: $version_label"
aws_cmd elasticbeanstalk create-application-version \
  --application-name "$application_name" \
  --version-label "$version_label" \
  --source-bundle "S3Bucket=${s3_bucket},S3Key=${s3_key}" \
  --process >/dev/null

log "Updating environment: $environment_name"
aws_cmd elasticbeanstalk update-environment \
  --application-name "$application_name" \
  --environment-name "$environment_name" \
  --version-label "$version_label" >/dev/null

log "Waiting for environment update"
aws_cmd elasticbeanstalk wait environment-updated \
  --application-name "$application_name" \
  --environment-names "$environment_name"

cname="$(aws_cmd elasticbeanstalk describe-environments \
  --application-name "$application_name" \
  --environment-names "$environment_name" \
  --query 'Environments[0].CNAME' \
  --output text)"

printf 'IMAGE_URI=%s\n' "$image_uri"
printf 'VERSION_LABEL=%s\n' "$version_label"
printf 'BUNDLE_ZIP=%s\n' "$bundle_zip"
printf 'CNAME=%s\n' "$cname"

if [[ "$skip_healthcheck" -eq 0 ]]; then
  log "Checking health endpoint: http://${cname}${health_path}"
  curl --fail --silent --show-error \
    --retry 12 \
    --retry-delay 10 \
    --retry-connrefused \
    "http://${cname}${health_path}" >/dev/null
fi

log "Deploy completed"
