#!/bin/bash

# Rogue Garmin Bridge - Auto-Update Script
# Checks GitHub for updates and redeploys if changes are found.
# Designed to run as a cron job on Raspberry Pi.
#
# Usage:
#   ./scripts/auto-update.sh                  # Check and update if needed
#   ./scripts/auto-update.sh --force          # Force redeploy even if no changes
#   ./scripts/auto-update.sh --check-only     # Only check, don't deploy
#
# Cron example (check every hour):
#   0 * * * * /home/pi/rogue_garmin_bridge/scripts/auto-update.sh >> /home/pi/rogue_garmin_bridge/logs/auto-update.log 2>&1
#
# Cron example (check every 15 minutes):
#   */15 * * * * /home/pi/rogue_garmin_bridge/scripts/auto-update.sh >> /home/pi/rogue_garmin_bridge/logs/auto-update.log 2>&1

set -e

# ── Configuration ─────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOCK_FILE="/tmp/rogue-garmin-bridge-update.lock"
BRANCH="${UPDATE_BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.rpi.yml}"
ENV_FILE="${ENV_FILE:-.env.rpi}"
MAX_LOG_SIZE=5242880  # 5MB

# ── Helpers ───────────────────────────────────────────────────────
timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

log() {
    echo "[$(timestamp)] [INFO] $1"
}

log_warn() {
    echo "[$(timestamp)] [WARN] $1"
}

log_error() {
    echo "[$(timestamp)] [ERROR] $1" >&2
}

log_success() {
    echo "[$(timestamp)] [OK] $1"
}

# ── Lock file (prevent concurrent updates) ────────────────────────
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null)
        if kill -0 "$LOCK_PID" 2>/dev/null; then
            log_warn "Another update is already running (PID $LOCK_PID). Exiting."
            exit 0
        else
            log_warn "Stale lock file found. Removing."
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

release_lock() {
    rm -f "$LOCK_FILE"
}

trap release_lock EXIT

# ── Log rotation ──────────────────────────────────────────────────
rotate_log() {
    local log_file="$LOG_DIR/auto-update.log"
    if [ -f "$log_file" ] && [ "$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null)" -gt "$MAX_LOG_SIZE" ]; then
        mv "$log_file" "$log_file.old"
        log "Log rotated"
    fi
}

# ── Parse arguments ───────────────────────────────────────────────
FORCE=false
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ── Main ──────────────────────────────────────────────────────────
cd "$PROJECT_DIR"
mkdir -p "$LOG_DIR"

acquire_lock
rotate_log

log "Starting update check (branch: $BRANCH)"

# Verify git repo
if [ ! -d ".git" ]; then
    log_error "Not a git repository: $PROJECT_DIR"
    exit 1
fi

# Fetch latest from remote
log "Fetching from origin..."
if ! git fetch origin "$BRANCH" 2>&1; then
    log_error "Failed to fetch from origin. Check network connectivity."
    exit 1
fi

# Compare local and remote
LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse "origin/$BRANCH")

log "Local:  $LOCAL_HASH"
log "Remote: $REMOTE_HASH"

if [ "$LOCAL_HASH" = "$REMOTE_HASH" ] && [ "$FORCE" = false ]; then
    log "Already up to date. No action needed."
    exit 0
fi

if [ "$FORCE" = true ] && [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
    log "No changes detected but --force specified. Redeploying."
fi

# Show what changed
if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
    COMMIT_COUNT=$(git rev-list --count "$LOCAL_HASH".."$REMOTE_HASH")
    log "Found $COMMIT_COUNT new commit(s):"
    git log --oneline "$LOCAL_HASH".."$REMOTE_HASH" | while read -r line; do
        log "  $line"
    done
fi

if [ "$CHECK_ONLY" = true ]; then
    log "Check-only mode. Updates available but not applying."
    exit 0
fi

# Pull changes
log "Pulling changes..."
if ! git pull origin "$BRANCH" 2>&1; then
    log_error "Git pull failed. There may be local changes conflicting with upstream."
    log_error "Try: git stash && git pull origin $BRANCH && git stash pop"
    exit 1
fi

# Rebuild and restart Docker containers
log "Rebuilding Docker containers..."
if [ -f "$COMPOSE_FILE" ]; then
    ENV_FLAG=""
    if [ -f "$ENV_FILE" ]; then
        ENV_FLAG="--env-file $ENV_FILE"
    fi

    docker compose -f "$COMPOSE_FILE" $ENV_FLAG build 2>&1

    log "Restarting containers..."
    docker compose -f "$COMPOSE_FILE" $ENV_FLAG up -d 2>&1

    # Wait for health check
    log "Waiting for application to start..."
    sleep 15

    APP_PORT="${APP_PORT:-5000}"
    if curl -sf "http://localhost:$APP_PORT/health" > /dev/null 2>&1; then
        log_success "Update complete. Application is healthy."
    else
        log_warn "Application may not be fully ready. Check logs: docker compose -f $COMPOSE_FILE logs"
    fi

    # Clean up old Docker images
    docker image prune -f > /dev/null 2>&1 || true
else
    log_error "Compose file not found: $COMPOSE_FILE"
    exit 1
fi

NEW_HASH=$(git rev-parse HEAD)
log_success "Updated from ${LOCAL_HASH:0:8} to ${NEW_HASH:0:8}"
