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

        columns = [c.strip() for c in df.columns.values]
        assert settings.EXCEL_PROMPT_COLUMN in columns
        try:
            assert settings.EXCEL_KEY_COLUMN in columns
        except AssertionError:
            pass
        else:
            do_keys = True
        
        prompt_col = df.columns.values[columns.index(settings.EXCEL_PROMPT_COLUMN)]
        product_sku_col = None
        if do_keys:
            product_sku_col = df.columns.values[columns.index(settings.EXCEL_KEY_COLUMN)]

    if do_keys:
        log.append('Product SKU column is detected.')
    else:
        log.append('Product SKU column is not detected.')

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
        prompt_text = str(row[prompt_col])
        prompt_key = str(row[product_sku_col]) if do_keys else None

        if prompt_key is not None:
            try:
                prompt_key = clean_html(prompt_key)
            except Exception as e:
                logger.warn(e)
                log.append(f'Skip: row: {i}, key: "{prompt_key}" ')
                continue

        try:
            prompt_text = clean_html(prompt_text)
        except Exception as e:
            logger.warn(e)
            log.append(f'Skip: row: {i}, text: "{prompt_text}" ')
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
