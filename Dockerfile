FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY /src /app/

EXPOSE 8000

COPY entrypoint.sh /app/
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]