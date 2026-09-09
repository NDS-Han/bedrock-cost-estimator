FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY config config
COPY migrations migrations
COPY alembic.ini start.sh ./
RUN chmod +x start.sh
EXPOSE 8000
CMD ["./start.sh"]
