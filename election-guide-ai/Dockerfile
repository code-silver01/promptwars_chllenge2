# ============================================================
# Election Guide AI — Production Docker Image
# Uses Python 3.11-slim for minimal image size on Cloud Run
# ============================================================
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install dependencies first (layer caching optimisation)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application source
COPY . .

# Cloud Run uses PORT env var; default to 8080
EXPOSE 8080
ENV PORT=8080

# Launch the FastAPI server with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
