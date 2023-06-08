# Chat GPT for e-shop
Chat GPT for Dalibor Cmolik e-shop (service).


# Setup


## First run
Manually execute following steps after `docker-compose up -d --build`. Use `docker exec -it  gpt /bin/bash`.
```
bash setup.sh
```

## Stop
Stop service with `docker-compose down`.

## Next run
Start again with `docker-compose up -d --build`. Execute manually following steps if needed.
```
python manage.py migrate
```