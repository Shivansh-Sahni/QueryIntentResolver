FROM python:3.11-slim

WORKDIR /app
COPY v1/requirements.txt /app/v1/requirements.txt
RUN pip install --no-cache-dir -r /app/v1/requirements.txt
COPY v1 /app/v1
ENV PYTHONPATH=/app/v1/src
ENV QIR_MODEL_PATH=/app/v1/artifacts/release/model.joblib
ENV QIR_POLICY_PATH=/app/v1/config/route_policy.json
EXPOSE 8000
CMD ["uvicorn", "qir_v1.api:app", "--host", "0.0.0.0", "--port", "8000"]
