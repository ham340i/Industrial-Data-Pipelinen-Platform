FROM python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /workspace
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --only-binary :all: --require-hashes -r requirements.lock \
    && groupadd --gid 10001 lps \
    && useradd --uid 10001 --gid lps --no-create-home lps \
    && mkdir -p /var/lib/lps \
    && chown lps:lps /var/lib/lps
COPY app/ ./app/
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
