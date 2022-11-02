FROM python:3.10-slim-buster

WORKDIR /app

RUN pip install uvicorn

COPY ./requirements.txt ./

RUN pip install --no-cache-dir --upgrade -r ./requirements.txt

COPY ./app ./app

COPY ./docker-entry.sh ./

# Non root user
USER 1 

EXPOSE 8080
ENTRYPOINT ["./docker-entry.sh"]