#!/usr/bin/bash

docker build -t pintopics . && \
  docker run -it --env-file .env pintopics:latest

