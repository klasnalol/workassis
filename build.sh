#!/usr/bin/env bash
DEFAULT_IMAGE_NAME='worky'
DEFAULT_CONTAINER_NAME='worky'
DEFAULT_PORT_MAPPING='5002:5002'

: "${IMAGE_NAME:=$DEFAULT_IMAGE_NAME}"
: "${CONTAINER_NAME:=$DEFAULT_CONTAINER_NAME}"
: "${PORT_MAPPING:=$DEFAULT_PORT_MAPPING}"

reset_color(){
    printf "\x1b[0m"
}

set_red(){
    printf "\x1b[31m"
}

set_green(){
    printf "\x1b[32m"
}
set_yellow(){
    printf "\x1b[33m"
}

set_blue(){
    printf "\x1b[34m"
}
set_purple(){
    printf "\x1b[35m"
}

log_colored() {
    set_purple && printf "[LOG] " && reset_color
    printf "$1" 
}

write_startup_info(){
    printf "Image: "
    set_blue
    echo $IMAGE_NAME
    reset_color

    printf "Container:"
    set_blue
    echo $CONTAINER_NAME
    reset_color

    printf "Ports:"
    set_blue
    echo $PORT_MAPPING
    reset_color
}



stop_container(){
    if [ $# == 0 ]; then
        local CHOSEN_CONTAINER_NAME=$CONTAINER_NAME
    else
        local CHOSEN_CONTAINER_NAME=$1
    fi
    set_purple && printf "[LOG]" && reset_color

    printf " Stopping and removing container: \"" && set_blue && printf "%s" $CHOSEN_CONTAINER_NAME && reset_color && echo "\""

    docker container stop $CHOSEN_CONTAINER_NAME && docker container rm $CHOSEN_CONTAINER_NAME && set_green && echo "[LOG] Successfully stopped $CHOSEN_CONTAINER_NAME" && reset_color
}

docker_build(){
    local IMAGE_VERSION="latest"
    if [ $# == 0 ]; then
        CHOSEN_IMAGE_NAME=$IMAGE_NAME
    else
        CHOSEN_IMAGE_NAME=$1
    fi
    log_colored "Building image: \"" && set_blue && printf "%s:%s" $CHOSEN_IMAGE_NAME $IMAGE_VERSION && reset_color && echo "\""

    docker build -t $CHOSEN_IMAGE_NAME:$IMAGE_VERSION .
}

docker_run(){
    if [[ $1 == "i"  ]]; then
        RUN_MODE='-it'
	RUN_MODE_NAME="interactive"
    else
        RUN_MODE='-d'
	RUN_MODE_NAME="background"
    fi
    
    log_colored "Starting container: \"" && set_blue && printf "$CONTAINER_NAME" && reset_color && printf "\" under mode: \"" && set_blue && printf "%s" $RUN_MODE_NAME && reset_color && echo "\""
    # echo "docker run --name $CONTAINER_NAME $RUN_MODE -p $PORT_MAPPING $IMAGE_NAME:latest"
    docker run --name $CONTAINER_NAME $RUN_MODE -p $PORT_MAPPING $IMAGE_NAME:latest 
}

build(){
    write_startup_info
    if [[ $# == 0 ]]; then
        stop_container
        docker_build && docker_run
    elif [[ $1 == "dev" ]]; then
	stop_container
        docker_build && docker_run "i"
    elif [[ $1 == "stop" ]]; then
        stop_container
    elif [[ $1 =~ i(nter(active)?)?  ]]; then
        stop_container
        docker_build && docker_run "i"
    else
        printf "Unknown option: \"%s\"\n" $1
    fi
}

build $*
