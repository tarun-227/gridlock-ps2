FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# XGBoost 3.x ships nvidia-nccl-cu12 as a dependency on Linux.
# The .so lives inside the Python package dir, not a standard linker path.
# Expose it so libxgboost.so can find libnccl.so.2 if it needs it.
ENV LD_LIBRARY_PATH="/usr/local/lib/python3.11/site-packages/nvidia/nccl/lib:${LD_LIBRARY_PATH:-}"

COPY . .

# Fail-fast: verify the ML pipeline is importable inside this image.
RUN python -c "\
import sys; sys.path.insert(0, '.'); \
from src.predict import predict_all; \
print('ML import OK');"

# Fail-fast: verify the FastAPI app itself loads cleanly (catches module-level crashes in api.py).
RUN python -c "\
import sys; sys.path.insert(0, '.'); \
from app.api import app; \
print('API import OK');"

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]
