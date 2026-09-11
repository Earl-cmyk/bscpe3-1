#!/bin/sh
set -eu

MODEL_PATH=/app/earLLM/models/model_artifact.json
PORT=${PORT:-10000}

/usr/local/bin/reinitialized --model "$MODEL_PATH" serve --bind 127.0.0.1:8787 &
EARLLM_PID=$!

cleanup() {
	kill "$EARLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

attempt=0
while [ "$attempt" -lt 30 ]; do
	if ! kill -0 "$EARLLM_PID" 2>/dev/null; then
		echo "earLLM exited before becoming ready" >&2
		exit 1
	fi
	if python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8787/health', timeout=1).read()"; then
		break
	fi
	attempt=$((attempt + 1))
	sleep 1
done

if [ "$attempt" -ge 30 ]; then
	echo "earLLM did not become ready" >&2
	exit 1
fi

exec gunicorn --bind "0.0.0.0:${PORT}" --workers 1 --timeout 120 run:app
