from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.http import HttpResponseBadRequest, HttpResponse

from gpt import models
from gpt.forms import UploadFileForm
from gpt.core.handlers import handle_uploaded_file

from threading import Thread, Event
from queue import Queue, Empty
from time import sleep

global_queue = Queue()
global_block_event = Event()
global_block_event.set()


def worker():
    while True:
        while global_queue.empty() and global_block_event.is_set():
            sleep(1)

        try:
            prompt, iteration = global_queue.get(block=False)
        except Empty:
            continue
        else:
            if global_queue.empty():
                print(f'Finish iteration: {global_queue.qsize()}')
                global_block_event.set()
                iteration.is_finished = True
                iteration.save()

            # completition = models.Competition()
            print(prompt, iteration)


global_worker_threads = [
    Thread(target=worker, daemon=True),
    Thread(target=worker, daemon=True),
    Thread(target=worker, daemon=True),
    Thread(target=worker, daemon=True),
    Thread(target=worker, daemon=True),
]

models.EvaluationIteration.finish_unfinished()
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
    datasets = models.Dataset.objects.all()
    dataset_info = []
    for dataset in datasets:
        dataset_info.append({
            'id': dataset.id,
            'tag': dataset.tag,
            'prompts_count_all': dataset.prompts_count_all,
            'prompts_count_enabled': dataset.prompts_count_enabled,
            'prompts_count_evaluated': dataset.prompts_count_evaluated,
            'created_at': dataset.created_at,
            'evaluations': dataset.num_evaluated,
            'status': 'Evaluating...' if dataset.is_evaluating else 'Ready',
            'action':  Action.stop if dataset.is_evaluating else Action.process
        })

    iteration_info = []
    iterations = models.EvaluationIteration.all_finished()
    for iteration in iterations:
        iteration_info.append({
            'id': iteration.id,
            'created_at': iteration.created_at,
            'created_by': iteration.created_by.username,
            'dataset_tag': iteration.dataset.tag,
            'model': iteration.model.model,
            'token': iteration.api.key,
            # TODO: count cost
        })

    model, api, status_message_content, status_message_severity = get_model_api()

    return render(request, "gpt/dashboard.html", {
        "api": api,
        "model": model,
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
    else:
        form = UploadFileForm()
    return render(request, "gpt/upload.html", {
        "form": form,
        "upload_message_content": upload_message_content,
        "upload_message_severity": upload_message_severity,
        "upload_log": upload_log,
    })


def gpt_action_view(request):
    if request.method == "POST":
        if models.EvaluationIteration.any_unfinished():
            return HttpResponseBadRequest('Another iteration in progress')

        try:
            ds_id = request.GET["ds_id"]
            action = request.GET["action"]
        except KeyError:
            return HttpResponseBadRequest('Not enough parameters.')

        if action not in [Action.stop, Action.process]:
            return HttpResponseBadRequest('Action unknown.')

        try:
            ds_id = int(ds_id)
        except ValueError:
            return HttpResponseBadRequest('ID format unknown.')

        try:
            ds = models.Dataset.objects.get(id=ds_id)
        except models.Dataset.DoesNotExist:
            return HttpResponseBadRequest('ID unknown.')

        model, api, *_ = get_model_api()

        try:
            assert model is not None
            assert api is not None
        except AssertionError:
            return HttpResponseBadRequest('Model/Api not found.')

        prompts = ds.prompts_nevaluated
        if not len(prompts):
            return HttpResponseBadRequest('No prompts for exist in dataset.')

        iteration = models.EvaluationIteration(
            dataset=ds, model=model, api=api, is_started=True)
        iteration.save_model(request)

        for prompt in prompts:
            global_queue.put([prompt, iteration])
        global_block_event.clear()

        return HttpResponse('ok')
