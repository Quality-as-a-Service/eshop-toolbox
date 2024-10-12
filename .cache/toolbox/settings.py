import logging
import os

from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            filename="app.log", mode="a", maxBytes=10 * (10**9), backupCount=10
        ),
    ],
)


[
    "gpt-4",
    "gpt-4-0314",
    "gpt-4-32k",
    "gpt-4-32k-0314",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-0301",
]
