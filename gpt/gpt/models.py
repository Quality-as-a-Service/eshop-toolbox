from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Sum


class GPTModel(models.Model):
    COMPATIBILITY_CHAT = 'chat'
    COMPATIBILITY_COMPLETION = 'completion'

    # Some models are ok with both modes, but for user it does nt matter
    COMPATIBILITY_MAP = {
        "text-davinci-003": COMPATIBILITY_COMPLETION,
        "text-davinci-002": COMPATIBILITY_COMPLETION,
        "text-curie-001": COMPATIBILITY_COMPLETION,
        "text-babbage-001": COMPATIBILITY_COMPLETION,
        "text-ada-001": COMPATIBILITY_COMPLETION,
        "gpt-4": COMPATIBILITY_CHAT,
        "gpt-4-0314": COMPATIBILITY_CHAT,
        "gpt-4-32k": COMPATIBILITY_CHAT,
        "gpt-4-32k-0314": COMPATIBILITY_CHAT,
        "gpt-3.5-turbo": COMPATIBILITY_CHAT,
        "gpt-3.5-turbo-0301": COMPATIBILITY_CHAT,
    }

    @property
    def compatibility(self):
        return self.COMPATIBILITY_MAP[self.model]

    # Model type, e.g. gpt-3.5-turbo
    model = models.CharField(max_length=100, unique=True, choices=[
                             ("text-davinci-003", "text-davinci-003"),
                             ("text-davinci-002", "text-davinci-002"),
                             ("text-curie-001", "text-curie-001"),
                             ("text-babbage-001", "text-babbage-001"),
                             ("text-ada-001", "text-ada-001"),
                             # https://platform.openai.com/docs/models/gpt-4
                             #  ("gpt-4", "gpt-4"),
                             #  ("gpt-4-0314", "gpt-4-0314"),
                             #  ("gpt-4-32k", "gpt-4-32k"),
                             #  ("gpt-4-32k-0314", "gpt-4-32k-0314"),
                             ("gpt-3.5-turbo", "gpt-3.5-turbo"),
                             ("gpt-3.5-turbo-0301", "gpt-3.5-turbo-0301")])
    # Only one model should be enabled
    is_enabled = models.BooleanField(default=False)

    prompt_token_cost = models.FloatField()  # dollars
    completition_token_cost = models.FloatField()  # dollars

    # Parameters
    p_temperature = models.FloatField(default=1, blank=True, verbose_name='Temperature', validators=[
        MinValueValidator(0),
        MaxValueValidator(2)
    ])
    p_max_length = models.BigIntegerField(
        verbose_name='Response max length (tokens)', default=None, null=True, blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10000)
        ])
    p_stop_sequences = models.TextField(
        verbose_name='Stop sequence', default=None, null=True, blank=True, help_text='Each sequence on a new line')

    p_top_p = models.FloatField(verbose_name='Top P', default=None, null=True, blank=True, validators=[
        MinValueValidator(0),
        MaxValueValidator(1)
    ])
    p_frequency_penalty = models.FloatField(verbose_name='Frequency penalty', default=None, blank=True, null=True, validators=[
        MinValueValidator(0),
        MaxValueValidator(2)
    ])
    p_presence_penalty = models.FloatField(verbose_name='Presence penalty', default=None, blank=True, null=True, validators=[
        MinValueValidator(0),
        MaxValueValidator(2)
    ])
    p_best_of = models.IntegerField(verbose_name='Best of', default=None, null=True, blank=True, validators=[
        MinValueValidator(0),
        MaxValueValidator(20)
    ])

    @property
    def p_stop_sequences_final(self):
        if self.p_stop_sequences is None:
            return None
        seq = [s.strip() for s in self.p_stop_sequences.strip().split('\n')]
        seq = [s for s in seq if s]
        return seq if len(seq) else None

    @property
    def parameters(self):
        if self.compatibility == self.COMPATIBILITY_COMPLETION:
            return [
                ['p_temperature', 'temperature'],
                ['p_max_length', 'max_tokens'],
                ['p_stop_sequences_final', 'stop'],
                ['p_top_p', 'top_p'],
                ['p_frequency_penalty', 'frequency_penalty'],
                ['p_presence_penalty', 'presence_penalty'],
                ['p_best_of', 'best_of'],
            ]
        elif self.compatibility == self.COMPATIBILITY_CHAT:
            return [
                ['p_temperature', 'temperature'],
                ['p_max_length', 'max_tokens'],
                ['p_top_p', 'top_p'],
                ['p_frequency_penalty', 'frequency_penalty'],
                ['p_presence_penalty', 'presence_penalty'],
            ]


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
    def completitions_count_errors(self):
        return self.completition_set.filter(is_error=True).count()

    @property
    def cost(self):
        total_completion_token_count = self.completition_set.aggregate(
            Sum('completition_token_count'))['completition_token_count__sum']
        total_prompt_token_count = self.completition_set.aggregate(
            Sum('prompt_token_count'))['prompt_token_count__sum']

        if total_completion_token_count is None or total_prompt_token_count is None:
            return 0

        return round((self.model.prompt_token_cost / 1000) * total_prompt_token_count
                     + (self.model.completition_token_cost / 1000) * total_completion_token_count, 10)


class Prompt(models.Model):
    # Prompt identifier for user (e.g. product sku)
    prompt_key = models.CharField(
        verbose_name='Prompt identifier', default=None, null=True, max_length=200)
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
        completion_cost = (self.evaluation_iteration.model.completition_token_cost / 1000) * \
            self.completition_token_count
        prompt_cost = (
            self.evaluation_iteration.model.prompt_token_cost / 1000) * self.prompt_token_count
        if self.is_error:
            return prompt_cost
        return prompt_cost + completion_cost
