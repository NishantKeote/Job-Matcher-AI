FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install torch==2.2.2+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html && \
    pip install -r requirements.txt

# Copy source
COPY . .

# Start app
# CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["sh", "-c", "uvicorn api.index:app --host 0.0.0.0 --port=$PORT"]

