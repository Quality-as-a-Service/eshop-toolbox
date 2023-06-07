from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Sum


class GPTModel(models.Model):
    # Model type, e.g. gpt-3.5-turbo
    model = models.CharField(max_length=100, unique=True)
    # Only one model should be enabled
    is_enabled = models.BooleanField(default=False)

    prompt_token_cost = models.FloatField()  # dollars
    completition_token_cost = models.FloatField()  # dollars

    # Parameters
    p_temperature = models.FloatField(default=1, verbose_name='Temperature', validators=[
        MinValueValidator(0),
        MaxValueValidator(2)
    ])
    p_max_length = models.BigIntegerField(
        verbose_name='Response max length (tokens)', default=None, null=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10000)
        ])
    p_stop_sequences = models.TextField(
        verbose_name='Stop sequence', default=None, null=True, help_text='Each sequence on a new line')

    p_top_p = models.FloatField(verbose_name='Top P', default=None, null=True, validators=[
        MinValueValidator(0),
        MaxValueValidator(1)
    ])
    p_frequency_penalty = models.FloatField(verbose_name='Frequency penalty', default=None, null=True, validators=[
        MinValueValidator(0),
        MaxValueValidator(2)
    ])
    p_best_of = models.IntegerField(verbose_name='Best of', default=None, null=True, validators=[
        MinValueValidator(0),
        MaxValueValidator(20)
    ])


class Api(models.Model):
    key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100, default='main')
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
    def prompts_count_enabled(self):
        return self.prompt_set.all().filter(is_enabled=True).count()

    @property
    def prompts_enabled(self):
        return self.prompt_set.all().filter(is_enabled=True).all()

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
    def any_unfinished(cls):
        return cls.objects.filter(is_finished=False).count()

    @property
    def status(self):
        if self.is_started and not self.is_finished:
            return 'in progress'
        elif self.is_started and self.is_finished:
            return 'finished'
        else:
            return 'not started'

    @property
    def prompts_count_enabled(self):
        return self.dataset.prompts_count_enabled

    @property
    def completitions_count_finished(self):
        return self.completition_set.count()

    @property
    def cost(self):
        total_completion_token_count = self.completition_set.aggregate(
            Sum('completition_token_count'))['completition_token_count__sum']
        total_prompt_token_count = self.completition_set.aggregate(
            Sum('prompt_token_count'))['prompt_token_count__sum']

        if total_completion_token_count is None or total_prompt_token_count is None:
            return 0

        return round(self.model.prompt_token_cost * total_prompt_token_count
                     + self.model.completition_token_cost * total_completion_token_count, 10)


class Prompt(models.Model):
    # Prompt identifier for user (e.g. product sku)
    prompt_key = models.CharField(verbose_name='Prompt identifier', default=None, null=True, max_length=200)
    # Source text from file
    prompt_text = models.TextField()
    # Disabled prompts are not going to be supplied to chat model
    is_enabled = models.BooleanField(default=True)

    dataset = models.ForeignKey(Dataset, on_delete=models.RESTRICT)


# https://platform.openai.com/docs/api-reference/completions
class Completition(models.Model):
    # Result from gpt
    # null means error in this completition
    completition_id = models.CharField(null=True, max_length=100, unique=True)
    completition_text = models.TextField(null=True)

    completition_token_count = models.IntegerField(null=True)
    prompt_token_count = models.IntegerField(blank=True, null=True)

    is_error = models.BooleanField(default=False)
    error_text = models.TextField(null=True)

    prompt = models.ForeignKey(Prompt, on_delete=models.RESTRICT)
    evaluation_iteration = models.ForeignKey(
        EvaluationIteration, on_delete=models.RESTRICT)

    @property
    def cost(self):
        return self.evaluation_iteration.model.prompt_token_cost * self.prompt_token_count \
            + self.evaluation_iteration.model.completition_token_cost * \
            self.completition_token_count
