#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/scale-app"
BACKEND_DIR="$ROOT_DIR/server"
VENV_DIR="$BACKEND_DIR/.venv"


# Detect device's primary IP address (IPv4, non-loopback)
get_device_ip() {
  ip route get 1 | awk '{for(i=1;i<=NF;i++) if ($i=="src") print $(i+1)}'
}

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8080}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-4173}"

# Auto-detect device IP for URLs if not set
DEVICE_IP=$(get_device_ip)
BACKEND_API_URL="${BACKEND_API_URL:-http://${DEVICE_IP}:${API_PORT}}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-http://${DEVICE_IP}:${WEB_PORT}}"

log() {
  printf "\n[%s] %s\n" "$(date +"%H:%M:%S")" "$1"
}

build_frontend() {
  log "Building frontend"
  cd "$FRONTEND_DIR"

  if [[ ! -f package-lock.json ]]; then
    npm install
  else
    npm ci
  fi

  cat > .env.production <<EOF
VITE_API_URL=${BACKEND_API_URL}
EOF

  npm run build
}

prepare_backend() {
  log "Preparing backend virtual environment"
  cd "$BACKEND_DIR"

  log "Installing system dependency: python3-picamera2"
  sudo apt-get update
  sudo apt-get install -y python3-picamera2

  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  pip install --upgrade pip
  pip install -r requirements.txt
}

start_backend() {
  log "Starting backend with Gunicorn on ${API_HOST}:${API_PORT}"
  cd "$BACKEND_DIR"
  export FRONTEND_ORIGIN

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  gunicorn --bind "${API_HOST}:${API_PORT}" --workers 2 --threads 4 --timeout 120 main:app &
  BACKEND_PID=$!
}

start_frontend() {
  log "Starting frontend preview on ${WEB_HOST}:${WEB_PORT}"
  cd "$FRONTEND_DIR"
  npm run preview -- --host "${WEB_HOST}" --port "${WEB_PORT}" --strictPort &
  FRONTEND_PID=$!
}

cleanup() {
  log "Stopping services"
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" || true
  fi
}

main() {
  build_frontend
  prepare_backend
  start_backend
  start_frontend

  log "Production stack is running"
  log "Frontend: ${FRONTEND_ORIGIN}"
  log "Backend:  ${BACKEND_API_URL}"
  log "Allowed CORS origin: ${FRONTEND_ORIGIN}"
  log "Press Ctrl+C to stop"

  trap cleanup INT TERM EXIT
  wait
}

main "$@"
