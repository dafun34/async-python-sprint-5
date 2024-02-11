FROM python:3.9

RUN apt-get -qq update && apt install --no-install-recommends  \
    -y curl libmagickwand-dev
RUN pip install --upgrade pip
ENV PYTHONPATH /src
WORKDIR /src
COPY requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt
COPY . /src
CMD ["python", "src"]
