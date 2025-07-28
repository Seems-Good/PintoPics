FROM alpine:latest AS build

RUN apk add --no-cache \
  python3 \
  py3-pip \
  && pip install --break-system-packages discord.py \
  && pip install --break-system-packages aiohttp

WORKDIR /app

COPY main.py /app/

CMD ["python3", "/app/main.py"]
