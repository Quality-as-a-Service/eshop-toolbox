import tempfile
import pandas as pd

from gpt import settings
from gpt import models


def handle_uploaded_file(request, payload, tag):
    log = []

    log.append('Import started.')
    with tempfile.TemporaryFile('wb+') as f:
        for chunk in payload.chunks():
            f.write(chunk)

        f.seek(0)
        df = pd.read_excel(f)

        assert settings.EXCEL_PROMPT_COLUMN in df.columns

    log.append('File format ok.')

    dataset = models.Dataset(tag=tag)
    dataset.save_model(request)
    log.append('Dataset created')

    prompts = []
    for i, row in df.iterrows():
        prompt_text = row[settings.EXCEL_PROMPT_COLUMN]
        try:
            prompt_text = str(prompt_text).strip()
        except:
            log.append(f'Skip: row: {i}, text: "{prompt_text}" ')
            continue
        prompt = models.Prompt(
            dataset=dataset,
            prompt_text=row[settings.EXCEL_PROMPT_COLUMN],
            is_enabled=True
        )
        prompts.append(prompt)
    # TODO - undo (limit for test)
    prompts = prompts[:10 if len(prompts) > 10 else len(prompts)]

    models.Prompt.objects.bulk_create(prompts)

    log.append(f'Import finished ({len(prompts)} prompts found).')

    return log
