from django.apps import AppConfig


class Config(AppConfig):
    name = 'gpt'
    verbose_name = "GPT App"

    def ready(self):
        from gpt import models

        EvaluationIteration = self.get_model("EvaluationIteration")
        EvaluationIteration.finish_unfinished()
        print('Finished all unfinished')
