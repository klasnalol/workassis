#!/usr/bin/env sh
docker container stop worky && docker container rm worky
docker build -t worky:latest . && docker run --name worky -d -p 5002:5002 worky:latest

