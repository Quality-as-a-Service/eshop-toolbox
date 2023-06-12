import tempfile
import pandas as pd

from django.db.utils import IntegrityError

from gpt import settings
from gpt import models
from gpt.utils import clean_html

import logging

logger = logging.getLogger('handlers')
logging.basicConfig(level=logging.INFO)


def handle_uploaded_file(request, payload, tag):
    log = []
    do_keys = False

    log.append('Import started.')

    with tempfile.TemporaryFile('wb+') as f:
        for chunk in payload.chunks():
            f.write(chunk)

        f.seek(0)
        if 'csv' in payload.name:
            df = pd.read_csv(f, delimiter=';')
            log.append('File extension csv detected.')
        elif 'xlsx' in payload.name:
            df = pd.read_excel(f)
            log.append('File extension excel detected.')
        else:
            log.append('File extension unknown.')
            return log

        assert settings.EXCEL_PROMPT_COLUMN in df.columns
        try:
            assert settings.EXCEL_KEY_COLUMN in df.columns
        except AssertionError:
            pass
        else:
            do_keys = True

    log.append('File format ok.')

    dataset = models.Dataset(tag=tag)
    try:
        dataset.save_model(request)
    except IntegrityError:
        log.append('Tag MUST be unique. Abort.')
        return log

    log.append('Dataset created')

    prompts = []
    for i, row in df.iterrows():
        prompt_text = str(row[settings.EXCEL_PROMPT_COLUMN])
        prompt_key = str(row[settings.EXCEL_KEY_COLUMN]) if do_keys else None

        try:
            prompt_text = clean_html(prompt_text)
        except Exception as e:
            logger.warn(e)
            log.append(f'Skip: row: {i}, text: "{prompt_text}" ')
            continue

        if prompt_key is not None:
            try:
                prompt_key = clean_html(prompt_key)
            except Exception as e:
                logger.warn(e)
                log.append(f'Skip: row: {i}, key: "{prompt_key}" ')
                continue

        prompt = models.Prompt(
            dataset=dataset,
            prompt_text=prompt_text,
            prompt_key=prompt_key,
            is_enabled=True
        )
        prompts.append(prompt)

    models.Prompt.objects.bulk_create(prompts)

    log.append(f'Import finished ({len(prompts)} prompts found).')

    return log
