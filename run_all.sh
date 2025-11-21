#!/bin/bash
# Script maestro: configura el AP ROBOMESHA y lanza backend + frontend en tmux
# Requisitos: nmcli (NetworkManager) y tmux instalados en la Raspberry Pi.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION="robomesha"
CON_NAME="ROBOMESHA"
SSID="ROBOMESHA"
PASSWORD="123456789"

ensure_tmux() {
  if ! command -v tmux >/dev/null 2>&1; then
    echo "⚠️  tmux no está instalado. Instálalo con: sudo apt install tmux"
    exit 1
  fi
}

ensure_ap_connection() {
  if ! nmcli -t -f NAME connection show | grep -Fx "$CON_NAME" >/dev/null 2>&1; then
    echo "📡 Creando conexión WiFi '${CON_NAME}' en modo AP..."
    sudo nmcli connection add \
      type wifi ifname wlan0 con-name "$CON_NAME" \
      autoconnect yes ssid "$SSID" \
      802-11-wireless.mode ap \
      802-11-wireless.band bg \
      ipv4.method shared \
      wifi-sec.key-mgmt wpa-psk \
      wifi-sec.psk "$PASSWORD"
  else
    echo "✅ Conexión '${CON_NAME}' ya existe."
  fi

  echo "🚀 Activando punto de acceso '${CON_NAME}'..."
  sudo nmcli connection up "$CON_NAME"
}

start_tmux_session() {
  if tmux has-session -t "$SESSION" >/dev/null 2>&1; then
    echo "ℹ️  Sesión tmux '${SESSION}' ya existía. Reiniciándola..."
    tmux kill-session -t "$SESSION"
  fi

  echo "🧠 Creando sesión tmux '${SESSION}'..."
  tmux new-session -d -s "$SESSION" -c "$ROOT_DIR" "./run_backend.sh"
  tmux new-window  -t "$SESSION" -c "$ROOT_DIR" "./run_frontend.sh"

  echo "✨ Sesión tmux lista. Ventanas:"
  echo "   - 0: backend"
  echo "   - 1: frontend"
  echo ""
  echo "📺 Adjuntando a tmux (Ctrl+B luego D para salir y mantener procesos vivos)..."
  tmux attach-session -t "$SESSION"
}

main() {
  ensure_tmux
  ensure_ap_connection
  start_tmux_session
}

main "$@"

