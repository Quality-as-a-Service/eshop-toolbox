from django.contrib import admin
from gpt import models

admin.site.register(models.GPTModel)
admin.site.register(models.Api)
admin.site.register(models.Dataset)
admin.site.register(models.Prompt)
admin.site.register(models.Competition)
admin.site.register(models.EvaluationIteration)
