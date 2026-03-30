Validate deploy composed bundle

Run rm -rf .deploy-fastapi
  rm -rf .deploy-fastapi
  mkdir -p .deploy-fastapi
  python3 - <<'PY'
  from pathlib import Path
  src = Path("deploy/eb/test-fastapi/docker-compose.yml").read_text()
  Path(".deploy-fastapi/docker-compose.yml").write_text(
      src.replace("__FASTAPI_IMAGE__", "tailtalk-fastapi:ci")
  )
  PY
  cat <<'EOF' > .deploy-fastapi/.env
  POSTGRES_DB=test_db
  POSTGRES_USER=test_user
  POSTGRES_PASSWORD=test_password
  POSTGRES_HOST=test-postgres
  POSTGRES_PORT=5432
  OPENAI_API_KEY=test-key
  DOCKER_USERNAME=
  DOCKER_PASSWORD=
  EOF
  docker compose -f .deploy-fastapi/docker-compose.yml --env-file .deploy-fastapi/.env config -q
  trap 'docker compose -f .deploy-fastapi/docker-compose.yml --env-file .deploy-fastapi/.env down -v --remove-orphans' EXIT
  docker compose -f .deploy-fastapi/docker-compose.yml --env-file .deploy-fastapi/.env up -d
  sleep 5
  curl --fail --silent --show-error --retry 12 --retry-delay 5 --retry-connrefused http://127.0.0.1/health
  shell: /usr/bin/bash -e {0}
  env:
    AWS_REGION: ap-northeast-2
    FASTAPI_IMAGE_REPO: kimheejoon91/test-tailtalk-fastapi
    FASTAPI_EB_APP_NAME: test-tailtalk-fastapi
    FASTAPI_EB_ENV_NAME: test-tailtalk-fastapi-env
    FASTAPI_HEALTH_PATH: /health
  
validating /home/runner/work/SKN22-Final-2Team-AI/SKN22-Final-2Team-AI/.deploy-fastapi/docker-compose.yml: services.fastapi additional properties 'auth' not allowed
Error: Process completed with exit code 1.