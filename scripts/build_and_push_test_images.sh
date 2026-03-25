#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
git_tag="$(git -C "$repo_root" rev-parse --short HEAD)"

django_repo="kimheejoon91/test-tailtalk-django"
fastapi_repo="kimheejoon91/test-tailtalk-fastapi"

build_and_push() {
  local context_dir="$1"
  local image_repo="$2"

  docker build \
    -t "${image_repo}:latest" \
    -t "${image_repo}:${git_tag}" \
    "$context_dir"

  docker push "${image_repo}:latest"
  docker push "${image_repo}:${git_tag}"
}

build_and_push "$repo_root/services/django" "$django_repo"
build_and_push "$repo_root/services/fastapi" "$fastapi_repo"

printf 'DJANGO_IMAGE=%s:%s\n' "$django_repo" "$git_tag"
printf 'FASTAPI_IMAGE=%s:%s\n' "$fastapi_repo" "$git_tag"
