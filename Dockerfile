FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000 7474 6333

CMD ["flask", "run", "--host=0.0.0.0"]
