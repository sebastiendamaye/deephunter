from django import forms
from .models import Repo

class RepoForm(forms.ModelForm):
    class Meta:
        model = Repo
        fields = ['name', 'url']
        widgets = {
            'name': forms.TextInput(attrs={'size': 50}),
            'url': forms.TextInput(attrs={'size': 100}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        url = cleaned_data.get('url')
        return cleaned_data
