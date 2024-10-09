import re
import pandas as pd

CLEAN_HTML = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')


def clean_html(txt):
    if pd.isnull(txt):
        raise RuntimeError('Prompt is none')
    txt = txt.replace('<br>', '\n').replace('<br/>', '\n')
    txt = re.sub(CLEAN_HTML, '', str(txt).strip())
    return txt


def clean_response(txt: str):
    txt = txt.strip()
    # Define the pattern to match special characters at the start of the string
    pattern = r'^[\W_]+'

    # Use regular expression substitution to remove special characters
    txt = re.sub(pattern, '', txt)

    return txt
