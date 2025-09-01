from django import forms
from .models import Repo

class RepoForm(forms.ModelForm):
    class Meta:
        model = Repo
        fields = ['name', 'url', 'is_private', 'token']
        widgets = {
            'name': forms.TextInput(attrs={'size': 50}),
            'url': forms.TextInput(attrs={'size': 100}),
            'token': forms.TextInput(attrs={'size': 100}),
        }
