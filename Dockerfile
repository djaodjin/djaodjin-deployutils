# syntax=docker/dockerfile:1
FROM python:3.7-slim-bullseye
ENV VIRTUAL_ENV="/opt/deployutils"
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin${PATH:+:}$PATH"
COPY . $VIRTUAL_ENV/djaodjin-deployutils/
WORKDIR $VIRTUAL_ENV/djaodjin-deployutils
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
ENTRYPOINT ["/opt/deployutils/bin/python", "/opt/deployutils/djaodjin-deployutils/manage.py", "runserver", "0.0.0.0:80"]
