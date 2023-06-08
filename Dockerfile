FROM python:3.8-slim-buster
EXPOSE 80

ENV DockerHOME=/home/app/webapp  
RUN mkdir -p $DockerHOME  
WORKDIR $DockerHOME  

RUN pip install --upgrade pip

COPY ./gpt $DockerHOME  
COPY ./.env $DockerHOME

RUN apt-get update
RUN apt-get install -y gcc python3-dev
RUN apt-get install -y libxml2-dev libxslt1-dev build-essential python3-lxml zlib1g-dev
RUN apt-get install -y default-mysql-client default-libmysqlclient-dev

RUN pip install -r requirements.txt

RUN bash setup.sh

CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]