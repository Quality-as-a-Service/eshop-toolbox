# E-shop toolbox
- Provide interface to use chat GPT to process large amount of text
- Provide crowlers to collect information from public sources

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
