# Same Python 3.12 base digest as the application workspace.
FROM python@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3
WORKDIR /experiment
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --only-binary :all: --require-hashes -r requirements.lock
COPY spike.py test_spike.py ./
ENV POLARS_MAX_THREADS=2 PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
CMD ["python", "spike.py"]
