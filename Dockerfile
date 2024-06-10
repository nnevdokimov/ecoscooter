FROM python:3.11

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update

RUN apt install gcc -y
RUN apt install python3-dev -y

RUN pip3 install --upgrade pip

ENV VIRTUAL_ENV=/opt/venv
RUN python3.11 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY ./requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Run the application:
COPY . /opt/app/
WORKDIR /opt/app/

