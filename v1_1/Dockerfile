FROM python:3.11-slim
WORKDIR /app
COPY v1_1/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && useradd --create-home --uid 10001 qir
COPY v1_1/qir_release /app/qir_release
COPY v1_1/artifacts/release /app/release
ENV QIR_BUNDLE=/app/release PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER qir
EXPOSE 8000
CMD ["uvicorn","qir_release.api:app","--host","0.0.0.0","--port","8000"]
