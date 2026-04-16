FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxslt-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p outputs

RUN mkdir -p /root/.streamlit && printf '[server]\nport = 8080\naddress = "0.0.0.0"\nheadless = true\nenableCORS = false\nenableXsrfProtection = false\n[browser]\ngatherUsageStats = false\n' > /root/.streamlit/config.toml

ENV GOOGLE_GENAI_USE_VERTEXAI=TRUE
ENV OUTPUTS_DIR=/app/outputs

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
