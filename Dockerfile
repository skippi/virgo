FROM python:3.7-slim

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_VERSION=1.1.5

RUN apt-get update && apt-get install -y curl
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
RUN ln -s ~/.poetry/bin/poetry /usr/local/bin/poetry

WORKDIR /app
COPY poetry.lock pyproject.toml /app/
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-dev
RUN poetry shell
COPY . /app

CMD poetry run virgo $VIRGO_TOKEN
