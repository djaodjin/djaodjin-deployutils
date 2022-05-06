# syntax=docker/dockerfile:1
FROM python:3.7-slim-bullseye
ENV VIRTUAL_ENV="/app"
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin${PATH:+:}$PATH"
COPY . $VIRTUAL_ENV/reps/djaodjin-deployutils/
WORKDIR $VIRTUAL_ENV/reps/djaodjin-deployutils
RUN set -eux;\
      apt-get update; \
      apt-get install -y --no-install-recommends make; \
      \
      pip install -r testsite/requirements.txt; \
      \
      make initdb; \
      \
      apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
      rm -rf /var/lib/apt/lists/*;
EXPOSE 80/tcp
ENTRYPOINT ["/app/bin/python", "/app/reps/djaodjin-deployutils/manage.py", "runserver", "0.0.0.0:80"]
