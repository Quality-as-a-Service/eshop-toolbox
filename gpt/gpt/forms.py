from django import forms


class UploadFileForm(forms.Form):
    tag = forms.CharField(max_length=50, help_text='Unique data name.')
    file = forms.FileField()