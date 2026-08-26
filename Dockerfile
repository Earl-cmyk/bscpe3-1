FROM rust:1.85-bookworm AS earllm-builder
WORKDIR /build/earLLM/rust
COPY earLLM/rust/Cargo.toml earLLM/rust/Cargo.lock* ./
COPY earLLM/rust/src ./src
RUN cargo build --release

FROM python:3.14-slim-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV EARLLM_URL=http://127.0.0.1:8787
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=earllm-builder /build/earLLM/rust/target/release/reinitialized /usr/local/bin/reinitialized
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]
