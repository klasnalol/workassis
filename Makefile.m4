#!/usr/bin/env make
define(`reset_color', printf "\x1b[0m")dnl
define(`set_red',printf "\x1b[31m")dnl
define(`set_green',printf "\x1b[32m")dnl
define(`set_yellow',printf "\x1b[33m")dnl
define(`set_blue',printf "\x1b[34m")dnl
define(`set_purple',printf "\x1b[35m")dnl
define(`log_colored',set_purple && printf "[LOG] " && reset_color && printf $1)dnl

IMAGE_NAME ?= worky
IMAGE_VERSION ?= latest
CONTAINER_NAME ?= worky
PORT_MAPPING ?= 5002:5002
RUN_MODE ?= -d

DOCKER_CLEAN_FORCE ?=


all: build_run

write_startup_info: 
	@printf "Image: " && printf "\x1b[34m" && echo $(IMAGE_NAME) && printf "\x1b[0m"
	@printf "Container:" && printf "\x1b[34m" && echo $(CONTAINER_NAME) && printf "\x1b[0m"
	@printf "Ports:" && printf "\x1b[34m" && echo $(PORT_MAPPING) && printf "\x1b[0m"



stop_container:
	@log_colored "Trying to stop container: \"$(CONTAINER_NAME)\"\n"
	@log_colored "Stopping and removing container: \"" && printf "\x1b[34m" && printf "%s" $(CONTAINER_NAME) && printf "\x1b[0m" && echo "\""
	@(docker container stop $(CONTAINER_NAME) || log_colored "Could not stop container: $(CONTAINER_NAME)\n") && (docker container rm $(CONTAINER_NAME) || log_colored  "Could not remove container: $(CONTAINER_NAME)\n") && log_colored "Successfully stopped $(CONTAINER_NAME)\n" 


docker_build: stop_container
	@log_colored "Building image: \"" && printf "\x1b[34m" && printf "%s:%s" $(IMAGE_NAME) $(IMAGE_VERSION) && printf "\x1b[0m" && echo "\""
	@docker build -t $(IMAGE_NAME):$(IMAGE_VERSION) .


docker_run: 
	@log_colored "Starting container: \"" && printf "\x1b[34m" && printf "$(CONTAINER_NAME)" && printf "\x1b[0m" && printf "\" under mode: \"" && printf "\x1b[34m" && printf "%s" $(RUN_MODE) && printf "\x1b[0m" && echo "\""
	@docker run --name $(CONTAINER_NAME) $(RUN_MODE) -p $(PORT_MAPPING) $(IMAGE_NAME):$(IMAGE_VERSION) 

docker_clean: 
	docker system prune $(DOCKER_CLEAN_FORCE)

build: write_startup_info docker_build

build_run: docker_build | docker_run

run:
	source bin/activate && python app.py


$(JS_MINIFIED): $(JS_SOURCE)
	for i in static/scripts/source/*.js; do j="$${i##*/}" && echo npx minify $$i -o "static/scripts/$${j%%.js}.min.js"; done

minify: $(JS_MINIFIED)


Makefile:
	m4 Makefile.m4 > Makefile
