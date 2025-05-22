FROM python:alpine

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for Cloud Run
ENV PORT 8080

# Expose the port
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

