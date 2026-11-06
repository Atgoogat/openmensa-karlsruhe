FROM python:3.14-slim

WORKDIR /app

COPY requirements.in ./
RUN pip install --no-cache-dir --upgrade -r requirements.in

COPY ./app ./app
COPY ./meta ./meta

COPY ./docker-entry.sh ./

# Non root user
USER 1

EXPOSE 8080
ENTRYPOINT ["./docker-entry.sh"]
