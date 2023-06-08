import re
import tempfile
import pandas as pd

from django.db.utils import IntegrityError

from gpt import settings
from gpt import models


CLEAN_HTML = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')


def clean(txt):
    if pd.isnull(txt):
        raise RuntimeError('Prompt is none')
    txt = re.sub(CLEAN_HTML, '', str(txt).strip())
    return txt


def handle_uploaded_file(request, payload, tag):
    log = []
    do_keys = False

    log.append('Import started.')
    with tempfile.TemporaryFile('wb+') as f:
        for chunk in payload.chunks():
            f.write(chunk)

        f.seek(0)
        df = pd.read_excel(f)

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
        prompt_text = row[settings.EXCEL_PROMPT_COLUMN]
        prompt_key = row[settings.EXCEL_KEY_COLUMN] if do_keys else None

        try:
            prompt_text = clean(prompt_text)
        except Exception as e:
            print(e)
            log.append(f'Skip: row: {i}, text: "{prompt_text}" ')
            continue

        if prompt_key is not None:
            try:
                prompt_key = clean(prompt_key)
            except:
                log.append(f'Skip: row: {i}, key: "{prompt_key}" ')
                continue

        prompt = models.Prompt(
            dataset=dataset,
            prompt_text=prompt_text,
            prompt_key=prompt_key,
            is_enabled=True
        )
        prompts.append(prompt)
    # TODO - undo (limit for test)
    prompts = prompts[:10 if len(prompts) > 10 else len(prompts)]

    models.Prompt.objects.bulk_create(prompts)

    log.append(f'Import finished ({len(prompts)} prompts found).')

    return log
