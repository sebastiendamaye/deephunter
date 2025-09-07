from django import forms
from django.forms import modelformset_factory
from .models import Connector, ConnectorConf

class ConnectorConfForm(forms.ModelForm):
    class Meta:
        model = ConnectorConf
        fields = ['key', 'value']
        widgets = {
            'key': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['key'].widget.attrs['title'] = self.instance.description

ConnectorConfFormSet = modelformset_factory(
    ConnectorConf,
    form=ConnectorConfForm,
    extra=0
)