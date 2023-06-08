from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.http import HttpResponseBadRequest, HttpResponse

from gpt import settings
from gpt import models
from gpt.forms import UploadFileForm
from gpt.core.handlers import handle_uploaded_file

from threading import Thread, Event
from queue import Queue, Empty
from time import sleep

from io import BytesIO
from django.http import HttpResponse

import pandas as pd
import openai
import logging

logger = logging.getLogger('views')
logging.basicConfig(level=logging.INFO)

global_queue = Queue()
global_block_event = Event()
global_block_event.set()


def add_not_none(pk, kwk, model, kw):
    if getattr(model, pk) is not None:
        kw[kwk] = getattr(model, pk)
    return kw


def worker(uid):
    w_logger = logging.getLogger(f'worker({uid})')

    w_logger.info('started')
    while True:
        while global_queue.empty() and global_block_event.is_set():
            sleep(1)

        try:
            prompt, iteration = global_queue.get(block=False)
        except Empty:
            continue
        else:
            w_logger.info(
                f'processing: {prompt.id} (queue size {global_queue.qsize()}): {prompt.prompt_text}')
            if global_queue.empty():
                w_logger.info(f'finish iteration: {iteration.id}')
                global_block_event.set()
                iteration.is_finished = True
                iteration.save()

            kw = {
                "model": iteration.model.model,
                "prompt": prompt.prompt_text
            }

            for pk, kwk in iteration.model.parameters:
                add_not_none(pk, kwk, iteration.model, kw)

            w_logger.warning(f'kw: {prompt.id}: {kw}')

            try:
                ai_completion = openai.Completion.create(**kw)
            except Exception as e:
                w_logger.warning(f'failed: {prompt.id}: {prompt.prompt_text}')
                db_completion = models.Completition(
                    prompt=prompt,
                    evaluation_iteration=iteration,
                    is_error=True,
                    error_text=str(e)
                )
                db_completion.save()
                continue

            w_logger.info(
                f'processed: {prompt.id} (queue size {global_queue.qsize()}): {ai_completion.choices[0].text}')

            db_completion = models.Completition(
                completition_id=ai_completion.id,
                completition_text=ai_completion.choices[0].text,
                completition_token_count=ai_completion.usage.completion_tokens,
                prompt_token_count=ai_completion.usage.prompt_tokens,
                prompt=prompt,
                evaluation_iteration=iteration,
            )

            db_completion.save()
            sleep(0.1)


global_worker_threads = [
    Thread(target=worker, daemon=True, args=[1]),
    Thread(target=worker, daemon=True, args=[2]),
    Thread(target=worker, daemon=True, args=[3]),
    Thread(target=worker, daemon=True, args=[4]),
    Thread(target=worker, daemon=True, args=[5]),
]

for th in global_worker_threads:
    th.start()


class Action:
    stop = 'stop'
    process = 'process'


def get_model_api():
    message_content = None
    message_severity = 'info'
    model = None
    api = None

    try:
        api = models.Api.objects.get(is_enabled=True)
    except models.Api.DoesNotExist:
        message_content = 'API Token not defined.'
        message_severity = 'danger'

    if api is not None:
        try:
            model = models.GPTModel.objects.get(is_enabled=True)
        except models.GPTModel.DoesNotExist:
            message_content = 'GPT Model not defined.'
            message_severity = 'danger'

    return model, api, message_content, message_severity


@csrf_protect
def gpt_dashboard_view(request):
    logger.info(f'{request.user} view dashboard')
    datasets = models.Dataset.objects.order_by('-created_at').all()
    dataset_info = []
    for dataset in datasets:
        dataset_info.append({
            'id': dataset.id,
            'tag': dataset.tag,
            'prompts_count_all': dataset.prompts_count_all,
            'prompts_count_enabled': dataset.prompts_count_enabled,
            'created_at': dataset.created_at,
            'evaluations': dataset.num_evaluated,
            'status': 'Evaluating...' if dataset.is_evaluating else 'Ready',
            'action':  Action.stop if dataset.is_evaluating else Action.process
        })

    iteration_info = []
    iterations = models.EvaluationIteration.objects.order_by(
        '-created_at').all()
    for iteration in iterations:
        iteration_info.append({
            'id': iteration.id,
            'created_at': iteration.created_at,
            'created_by': iteration.created_by.username,
            'dataset_tag': iteration.dataset.tag,
            'model': iteration.model.model,
            'token': iteration.api.name,
            'status': iteration.status,
            'prompts_enabled': iteration.prompts_count_enabled,
            'completitions_finished': iteration.completitions_count_finished,
            'completitions_error': iteration.completitions_count_errors,
            'cost': iteration.cost,
        })

    model, api, status_message_content, status_message_severity = get_model_api()

    model_detail = []
    if model is not None:
        for pk, _ in model.parameters:
            pv = getattr(model, pk)

            if pv is None:
                pv = '-default-'

            model_detail.append(f'{pk}: {pv}')
    model_detail = '\n'.join(model_detail)

    return render(request, "gpt/dashboard.html", {
        "api": api,
        "model": model,
        "model_detail": model_detail,
        "dataset_info": dataset_info,
        "iteration_info": iteration_info,
        "status_message_content": status_message_content,
        "status_message_severity": status_message_severity,
    })


@csrf_exempt
def gpt_upload_view(request):
    return _gpt_upload_view(request)


@csrf_protect
def _gpt_upload_view(request):
    upload_message_content = None
    upload_message_severity = 'info'
    upload_log = None

    if request.method == "POST":
        logger.info(f'{request.user} start upload dataset')

        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                upload_log = handle_uploaded_file(
                    request, request.FILES["file"], form.cleaned_data['tag'])
            except ValueError:
                upload_message_content = 'Failed to process. File format not valid.'
                upload_message_severity = 'danger'
            except AssertionError:
                upload_message_content = 'Failed to process. Content of file not valid.'
                upload_message_severity = 'danger'
        logger.info(f'{request.user} uploaded dataset')

    else:
        logger.info(f'{request.user} view upload page')
        form = UploadFileForm()
    return render(request, "gpt/upload.html", {
        "excel_prompt_col": settings.EXCEL_PROMPT_COLUMN,
        "excel_prompt_key": settings.EXCEL_KEY_COLUMN,
        "form": form,
        "upload_message_content": upload_message_content,
        "upload_message_severity": upload_message_severity,
        "upload_log": upload_log,
    })


def gpt_action_view(request):
    if request.method == "POST":
        logger.info(f'{request.user} trigger action')

        if models.EvaluationIteration.any_unfinished():
            logger.info(
                f'{request.user} unfinished iteration detected - abort')
            return HttpResponseBadRequest('Another iteration in progress')

        try:
            ds_id = request.GET["ds_id"]
            action = request.GET["action"]
        except KeyError:
            logger.info(f'{request.user} bad request')
            return HttpResponseBadRequest('Not enough parameters.')

        if action not in [Action.stop, Action.process]:
            logger.info(f'{request.user} bad action')
            return HttpResponseBadRequest('Action unknown.')

        if action == Action.process:
            logger.warning(f'{request.user} trigger process action')
            try:
                ds_id = int(ds_id)
            except ValueError:
                logger.info(f'{request.user} bad id')
                return HttpResponseBadRequest('ID format unknown.')

            try:
                ds = models.Dataset.objects.get(id=ds_id)
            except models.Dataset.DoesNotExist:
                logger.info(f'{request.user} unknown id')
                return HttpResponseBadRequest('ID unknown.')

            model, api, *_ = get_model_api()

            try:
                assert model is not None
                assert api is not None
            except AssertionError:
                logger.info(f'{request.user} model / api not found')
                return HttpResponseBadRequest('Model/Api not found.')

            openai.api_key = api.key

            prompts = ds.prompts_enabled
            if not len(prompts):
                logger.info(f'{request.user} ')
                return HttpResponseBadRequest('No prompts for exist in dataset.')

            logger.info(f'{request.user} register request')
            iteration = models.EvaluationIteration(
                dataset=ds, model=model, api=api, is_started=True)
            iteration.save_model(request)

            logger.info(f'{request.user} register prompts')
            for prompt in prompts:
                global_queue.put([prompt, iteration])
            global_block_event.clear()
            logger.info(f'{request.user} trigger processing')

        elif action == Action.stop:
            logger.warning(f'{request.user} trigger stop action')

            global_block_event.set()
            while not global_queue.empty():
                try:
                    global_queue.get(block=False)
                except Empty:
                    pass

        return HttpResponse('ok')


def gpt_completition_download(request):
    if request.method == "GET":
        try:
            itr_id = request.GET["itr_id"]
        except KeyError:
            return HttpResponseBadRequest('Not enough parameters.')

        try:
            itr_id = int(itr_id)
        except ValueError:
            return HttpResponseBadRequest('ID format unknown.')

        try:
            iteration = models.EvaluationIteration.objects.get(id=itr_id)
        except models.EvaluationIteration.DoesNotExist:
            return HttpResponseBadRequest('ID unknown.')

        df = []
        for c in iteration.completition_set.all():
            df.append({
                settings.EXCEL_KEY_COLUMN: c.prompt.prompt_key or '',
                'prompt_text': c.prompt.prompt_text,
                'completion_text': c.completition_text,
                'error': c.error_text
            })

        df = pd.DataFrame(df)

        f = BytesIO()
        df.to_excel(f)
        f.seek(0)

        response = HttpResponse(
            f.read(), content_type="application/vnd.ms-excel")
        response['Content-Disposition'] = f'inline; filename=iteration-{iteration.id}.xlsx'

        return response


def gpt_manual_view(request):
    if request.method == "GET":
        return render(request, "gpt/manual.html")
