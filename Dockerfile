FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home riskr
COPY app.py .
COPY riskr ./riskr
COPY templates ./templates
COPY static ./static
RUN mkdir /app/instance && chown riskr:riskr /app/instance
USER riskr
ENV RISKR_CONTAINER=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["python", "app.py", "run"]
