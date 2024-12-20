FROM alpine:latest

EXPOSE 5002

RUN apk update
RUN apk upgrade
RUN apk add python3 portaudio-dev

RUN adduser -D app

RUN mkdir /home/app/app
WORKDIR /home/app/app

COPY --chown=app:app . .
RUN chown app -R /home/app

USER app
RUN python3 -m venv .
RUN source bin/activate && pip install -r requirements.txt

RUN chmod +x ./startup.sh 
CMD [ "sh", "./startup.sh" ]