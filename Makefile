#!/usr/bin/env make

IMAGE_NAME ?= worky
IMAGE_VERSION ?= latest
CONTAINER_NAME ?= worky
PORT_MAPPING ?= 5002:5002
RUN_MODE ?= -d

DOCKER_CLEAN_FORCE ?=

HOST_URL=http://0.0.0.0:5002

JS_SCRIPTS_DIR = static/scripts
JS_SOURCE = $(wildcard $(JS_SCRIPTS_DIR)/source/*.js)

JS_MINIFIED_DIR=static/scripts/minified
JS_MINIFIED = $(foreach name,$(basename $(notdir $(JS_SOURCE))), $(JS_MINIFIED_DIR)/$(name).min.js)

JS_PRETTYFY_SRC=$(JS_SOURCE)
JS_PRETTIFY_FLAGS=-o "static/scripts/minified/$${j%%.js}.min.js" -c --source-map "filename='$${j%%.js}.min.js.map',root='/',url='$${j%%.js}.min.js.map'" 

CERTS_DIR=certs

VENV_FILES = include lib/ lib64 bin/ pyvenv.cfg

all: build_run

help:
	@echo "Usage: make [target]"
	@echo -e "[target] is what you want to make. It is one of:\n"
	@echo -e " minify:\tbuilds minified JS files."
	@echo -e " prettify:\tformats js source files."
	@echo ""
	@echo -e " certs:\tcreates certificates to use for HTTPS with flask"
	@echo ""
	@echo -e " build:\tBuilds docker image"
	@echo -e " build_run:\tBuilds docker container and starts it"
	@echo ""
	@echo -e " run:\tEnters python venv and starts the app"

write_startup_info: 
	@printf "Image: " && printf "\x1b[34m" && echo $(IMAGE_NAME) && printf "\x1b[0m"
	@printf "Container:" && printf "\x1b[34m" && echo $(CONTAINER_NAME) && printf "\x1b[0m"
	@printf "Ports:" && printf "\x1b[34m" && echo $(PORT_MAPPING) && printf "\x1b[0m"


node_modules: 
	npm install

npm-libs: node_modules

$(JS_MINIFIED_DIR):
	mkdir $(JS_MINIFIED_DIR)

$(JS_MINIFIED): $(JS_SOURCE) $(JS_MINIFIED_DIR) npm-libs
	@printf "\x1b[35m" && printf "[LOG]" && printf "\x1b[0m" && printf ' miniying js files: "' && printf "\x1b[34m" && printf '$(JS_SOURCE)' && printf "\x1b[0m" && echo '"'
	@for i in static/scripts/source/*.js; do (j="$${i##*/}" && npx uglifyjs $$i $(JS_PRETTIFY_FLAGS) &); done

minify: $(JS_MINIFIED)

prettify: $(JS_PRETTYFY_SRC)
	for file in $(JS_PRETTYFY_SRC); do npx prettier $$file --write; done 


stop_container:
	@printf "\x1b[35m" && printf "[LOG] " && printf "\x1b[0m" && printf  "Trying to stop container: \"$(CONTAINER_NAME)\"\n"
	@printf "\x1b[35m" && printf "[LOG] " && printf "\x1b[0m" && printf  "Stopping and removing container: \"" && printf "\x1b[34m" && printf "%s" $(CONTAINER_NAME) && printf "\x1b[0m" && echo "\""
	@(docker container stop $(CONTAINER_NAME) || printf "\x1b[35m" && printf "[LOG] " && printf "\x1b[0m" && printf  "Could not stop container: $(CONTAINER_NAME)\n") && (docker container rm $(CONTAINER_NAME) || printf "\x1b[35m" && printf "[LOG] " && printf "\x1b[0m" && printf   "Could not remove container: $(CONTAINER_NAME)\n") && printf "\x1b[35m" && printf "[LOG] " && printf "\x1b[0m" && printf  "Successfully stopped $(CONTAINER_NAME)\n" 


docker_build: stop_container minify
	@printf "\x1b[35m" && printf "[LOG] " && printf "\x1b[0m" && printf  "Building image: \"" && printf "\x1b[34m" && printf "%s:%s" $(IMAGE_NAME) $(IMAGE_VERSION) && printf "\x1b[0m" && echo "\""
	@docker build -t $(IMAGE_NAME):$(IMAGE_VERSION) .


docker_run: 
	@printf "\x1b[35m" && printf "[LOG] " && printf "\x1b[0m" && printf  "Starting container: \"" && printf "\x1b[34m" && printf "$(CONTAINER_NAME)" && printf "\x1b[0m" && printf "\" under mode: \"" && printf "\x1b[34m" && printf "%s" $(RUN_MODE) && printf "\x1b[0m" && echo "\""
	@docker run --name $(CONTAINER_NAME) $(RUN_MODE) -p $(PORT_MAPPING) $(IMAGE_NAME):$(IMAGE_VERSION) 

docker_clean: 
	docker system prune $(DOCKER_CLEAN_FORCE)

build: write_startup_info docker_build

build_run: docker_build | docker_run

certs: 
	mkdir -p $(CERTS_DIR)
	openssl req -x509 -newkey rsa:4096 -nodes -out $(CERTS_DIR)/cert.pem -keyout $(CERTS_DIR)/key.pem -days 365

run: minify 
	source bin/activate && python app.py

$(VENV_FILES):
	python3 -m venv .

start-venv: $(VENV_FILES)

python-libs: start-venv
	. bin/activate && pip install -r requirements.txt

remove-venv:
	rm -rf $(VENV_FILES)

setup: python-libs certs minify
