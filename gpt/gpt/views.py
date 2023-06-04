from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from gpt import models
from gpt.forms import UploadFileForm
from gpt.core.handlers import handle_uploaded_file


def gpt_dashboard_view(request):
    status_message_content = None
    status_message_severity = 'info'

    api = None
    model = None

    datasets = models.Dataset.objects.all()
    dataset_info = []
    for dataset in datasets:
        dataset_info.append({
            'id': dataset.id,
            'tag': dataset.tag,
            'prompts_count_all': dataset.prompts_count_all,
            'created_at': dataset.created_at,
            'status': 'ok',
        })

    try:
        api = models.Api.objects.get(is_enabled=True)
    except models.Api.DoesNotExist:
        status_message_content = 'API Token not defined.'
        status_message_severity = 'danger'

    if api is not None:
        try:
            model = models.GPTModel.objects.get(is_enabled=True)
        except models.GPTModel.DoesNotExist:
            status_message_content = 'GPT Model not defined.'
            status_message_severity = 'danger'

    return render(request, "gpt/dashboard.html", {
        "api": api,
        "model": model,
        "dataset_info": dataset_info,
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
                    request.FILES["file"], form.cleaned_data['tag'])
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
