from django.db import models
from django.contrib.auth.models import User


class GPTModel(models.Model):
    # Model type, e.g. gpt-3.5-turbo
    model = models.CharField(max_length=100, unique=True)
    # Only one model should be enabled
    is_enabled = models.BooleanField(default=False)
    prompt_token_cost = models.FloatField()  # dollars
    competition_token_cost = models.FloatField()  # dollars


class Api(models.Model):
    key = models.CharField(max_length=100, unique=True)
    # Only one key should be enabled
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Dataset(models.Model):
    tag = models.CharField(max_length=50, unique=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.RESTRICT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def prompts_count_all(self):
        return self.prompt_set.count()

    @property
    def prompts_count_evaluated(self):
        return self.prompt_set.all().filter(is_evaluated=True).count()

    @property
    def prompts_count_evaluated(self):
        return self.prompt_set.all().filter(is_evaluated=True).count()

    @property
    def prompts_nevaluated(self):
        return self.prompt_set.all().filter(is_evaluated=False, is_enabled=True).all()

    @property
    def prompts_count_enabled(self):
        return self.prompt_set.all().filter(is_enabled=True).count()

    @property
    def is_evaluating(self):
        return self.evaluationiteration_set.all().filter(is_started=True, is_finished=False).count() > 0

    @property
    def num_evaluated(self):
        return self.evaluationiteration_set.all().filter(is_started=True, is_finished=True).count()

    def save_model(self, request):
        self.created_by = request.user
        self.save()

# Whenever bulk request to model is made it should be registered as prompt iteration


class EvaluationIteration(models.Model):
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.RESTRICT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_started = models.BooleanField(default=False)
    is_finished = models.BooleanField(default=False)

    dataset = models.ForeignKey(Dataset, on_delete=models.RESTRICT)
    model = models.ForeignKey(GPTModel, on_delete=models.RESTRICT)
    api = models.ForeignKey(Api, on_delete=models.RESTRICT)

    def save_model(self, request):
        self.created_by = request.user
        self.save()

    # In case server fail stop all iterations on start
    @classmethod
    def finish_unfinished(cls):
        for iteration in cls.objects.filter(is_finished=False).all():
            iteration.is_finished = True
            iteration.save()

    @classmethod
    def all_finished(cls):
        return cls.objects.filter(is_finished=True).all()

    @classmethod
    def any_unfinished(cls):
        return cls.objects.filter(is_finished=False).count()

    # TODO: count prompts in progress


class Prompt(models.Model):
    # Source text from file
    prompt_text = models.TextField()
    # Filled after request
    prompt_token_count = models.IntegerField(blank=True, null=True)

    # Disabled prompts are not going to be supplied to chat model
    is_enabled = models.BooleanField(default=True)
    # As soon as passed to chat GPT should be marked as evaluated
    is_evaluated = models.BooleanField(default=False)

    dataset = models.ForeignKey(Dataset, on_delete=models.RESTRICT)


# https://platform.openai.com/docs/api-reference/completions
class Competition(models.Model):
    # Result from gpt
    competition_id = models.CharField(max_length=100, unique=True)
    competition_text = models.TextField()
    competition_token_count = models.IntegerField()

    prompt = models.ForeignKey(Prompt, on_delete=models.RESTRICT)
    evaluation_iteration = models.ForeignKey(
        EvaluationIteration, on_delete=models.RESTRICT)
