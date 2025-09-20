from django import forms
from django.forms import modelformset_factory
from .models import Connector, ConnectorConf

class ConnectorConfForm(forms.ModelForm):
    class Meta:
        model = ConnectorConf
        fields = ['value']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:

            # Set widget for 'value' based on fieldtype
            fieldtype = getattr(self.instance, 'fieldtype', None)
            if fieldtype == 'int':
                self.fields['value'].widget = forms.NumberInput()
            elif fieldtype == 'float':
                self.fields['value'].widget = forms.NumberInput(attrs={'step': 'any'})
            elif fieldtype == 'char':
                self.fields['value'].widget = forms.Textarea()
            elif fieldtype == 'bool':
                self.initial['value'] = None
                if self.instance.value.lower() in ['true', '1', 'yes']:
                    self.fields['value'].widget = forms.CheckboxInput(attrs={'checked': True})
                else:
                    self.fields['value'].widget = forms.CheckboxInput(attrs={'checked': False})
            elif fieldtype == 'email':
                self.fields['value'].widget = forms.EmailInput()
            elif fieldtype == 'ipaddress':
                self.fields['value'].widget = forms.TextInput(attrs={'pattern': r'^\d{1,3}(\.\d{1,3}){3}$'})
            elif fieldtype == 'password':
                self.fields['value'].widget = forms.Textarea(attrs={
                    'readonly': True,
                    'data-actual': self.instance.value,
                    'class': 'password-field',
                })
                self.initial['value'] = '********'
            elif fieldtype == 'url':
                self.fields['value'].widget = forms.URLInput(attrs={'class': 'url-field'})

ConnectorConfFormSet = modelformset_factory(
    ConnectorConf,
    form=ConnectorConfForm,
    extra=0
)