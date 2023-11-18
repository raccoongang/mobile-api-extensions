FROM python:3.8-slim-bullseye as base-image

ENV PYTHONUNBUFFERED 1
RUN apt update -y && apt install make

WORKDIR /app

FROM base-image as test-image

COPY requirements/test.txt requirements/test.txt
RUN pip install -r requirements/test.txt


FROM base-image as build-box

COPY requirements/pypi.txt requirements/pypi.txt
RUN pip install -r requirements/pypi.txt
