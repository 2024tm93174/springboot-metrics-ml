FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files
COPY . .

# Default: run real-time monitoring
CMD ["python", "real_time.py"]

########     COPY model.pkl .