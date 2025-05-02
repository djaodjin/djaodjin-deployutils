# syntax=docker/dockerfile:1
FROM python:3.10-slim-bookworm
#2025-04-15: python:3.10-slim-bookworm - Python 3.10.17, Debian 12.10 (Bookworm)
#2023-04-21: python:3.10-slim-bullseye - Python 3.10.11, Debian 11.0 (Bullseye)

LABEL org.opencontainers.image.source https://github.com/djaodjin/djaodjin-deployutils

# Print version info for build log
RUN echo "Building with" `python --version` '('`which python`')' "on Debian" `cat /etc/debian_version` "..."

# ==== Installs required native packages
RUN apt-get update -y
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends sqlite3

RUN python -m venv /app
# Make sure a 'db.sqlite' file exists in '.' if you want to launch the container
# without referencing an external database.
COPY . /app/reps/djaodjin-deployutils
WORKDIR /app/reps/djaodjin-deployutils
RUN /app/bin/pip install -r testsite/requirements.txt

EXPOSE 80/tcp
ENTRYPOINT ["/app/bin/python", "/app/reps/djaodjin-deployutils/manage.py", "runserver", "--nothreading", "--noreload", "0.0.0.0:80"]
