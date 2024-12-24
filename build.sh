#!/usr/bin/env sh
(docker build -t worky:latest . && docker run --name worky -it -p 5002:5002 worky:latest) || (docker container stop worky && docker container rm worky)
