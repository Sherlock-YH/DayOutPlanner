FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port 8000
EXPOSE 8000

# Bind Uvicorn to 0.0.0.0 so host and frontend requests reach FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]