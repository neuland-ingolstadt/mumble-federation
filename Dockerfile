FROM python:3

WORKDIR /usr/src/app

RUN apt update && \
    apt install -y opus-tools && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./mumble-federation.py" ]
