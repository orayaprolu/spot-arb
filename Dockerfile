FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m venv venv \
  && . venv/bin/activate \
  && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PATH="/app/venv/bin:$PATH"

CMD ["python", "-u", "-m", "app.main"]
