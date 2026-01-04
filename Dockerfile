FROM python:3.14-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir
COPY . .
EXPOSE 9090
CMD ["python", "order.py"]
