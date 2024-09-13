# syntax=docker/dockerfile:1
FROM python:3.7-slim-bullseye

RUN python -m venv /app
COPY . /app/reps/djaodjin-deployutils
WORKDIR /app/reps/djaodjin-deployutils
RUN /app/bin/pip install -r testsite/requirements.txt

EXPOSE 80/tcp
ENTRYPOINT ["/app/bin/python", "/app/reps/djaodjin-deployutils/manage.py", "runserver", "0.0.0.0:80"]
