from django import forms
from .models import Review, Analytic, SavedSearch, Tag, ThreatName, ThreatActor, Vulnerability
from connectors.models import Connector

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        exclude = ['analytic', 'reviewer']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 5, 'cols': 100}),
        }

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        comments = cleaned_data.get('comments')
        if decision == 'PENDING' and not comments:
            self.add_error('comments', 'Comments are required when decision is "Need to be updated".')
        return cleaned_data


class EditAnalyticDescriptionForm(forms.ModelForm):
    class Meta:
        model = Analytic
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 8, 'cols': 150}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        description = cleaned_data.get('description')
        return cleaned_data
    
class EditAnalyticNotesForm(forms.ModelForm):
    class Meta:
        model = Analytic
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 8, 'cols': 150}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        notes = cleaned_data.get('notes')
        return cleaned_data
    
class EditAnalyticQueryForm(forms.ModelForm):
    class Meta:
        model = Analytic
        fields = ['query', 'columns']
        widgets = {
            'query': forms.Textarea(attrs={'rows': 8, 'cols': 150}),
            'columns': forms.Textarea(attrs={'rows': 8, 'cols': 150}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        query = cleaned_data.get('query')
        columns = cleaned_data.get('columns')
        return cleaned_data

class SavedSearchForm(forms.ModelForm):
    class Meta:
        model = SavedSearch
        fields = ['name', 'description', 'search', 'is_public', 'is_locked']
        widgets = {
            'name': forms.TextInput(attrs={'size': 100}),
            'description': forms.Textarea(attrs={'rows': 3, 'cols': 100}),
            'search': forms.Textarea(attrs={'rows': 3, 'cols': 100}),
        }

class AnalyticForm(forms.ModelForm):
    class Meta:
        model = Analytic
        exclude = ['repo', 'created_by', 'pub_date', 'maxhosts_count', 'query_error', 'query_error_message', 'query_error_date', 'next_review_date', 'last_time_seen']
        widgets = {
            'name': forms.TextInput(attrs={'size': 100}),
            'description': forms.Textarea(attrs={'rows': 5, 'cols': 100}),
            'notes': forms.Textarea(attrs={'rows': 5, 'cols': 100}),
            'query': forms.Textarea(attrs={'rows': 5, 'cols': 100}),
            'columns': forms.Textarea(attrs={'rows': 5, 'cols': 100}),
            'emulation_validation': forms.Textarea(attrs={'rows': 5, 'cols': 100}),
            'references': forms.Textarea(attrs={'rows': 5, 'cols': 100}),
            'anomaly_threshold_count': forms.TextInput(attrs={'size': 3}),
            'anomaly_threshold_endpoints': forms.TextInput(attrs={'size': 3}),
        }

    def __init__(self, *args, allowed_status_choices=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit status choices to DRAFT and PUB
        if allowed_status_choices is not None:
            self.fields['status'].choices = [
                choice for choice in self.fields['status'].choices
                if choice[0] in allowed_status_choices
            ]

        self.fields['connector'].queryset = Connector.objects.filter(domain='analytics', enabled=True)
        
        self.fields['tags'].queryset = self.fields['tags'].queryset.model.objects.all()
        self.fields['tags'].widget.attrs.update({'class': 'form-select', 'data-placeholder': 'Choose Tags'})

        self.fields['mitre_techniques'].queryset = self.fields['mitre_techniques'].queryset.model.objects.all()
        self.fields['mitre_techniques'].widget.attrs.update({'class': 'form-select', 'data-placeholder': 'Choose MITRE Techniques'})

        self.fields['threats'].queryset = self.fields['threats'].queryset.model.objects.all()
        self.fields['threats'].widget.attrs.update({'class': 'form-select', 'data-placeholder': 'Choose Threats'})

        self.fields['actors'].queryset = self.fields['actors'].queryset.model.objects.all()
        self.fields['actors'].widget.attrs.update({'class': 'form-select', 'data-placeholder': 'Choose Threat Actors'})

        self.fields['target_os'].queryset = self.fields['target_os'].queryset.model.objects.all()
        self.fields['target_os'].widget.attrs.update({'class': 'form-select', 'data-placeholder': 'Choose Target OS'})

        self.fields['vulnerabilities'].queryset = self.fields['vulnerabilities'].queryset.model.objects.all()
        self.fields['vulnerabilities'].widget.attrs.update({'class': 'form-select', 'data-placeholder': 'Choose Vulnerabilities'})

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']

class ThreatForm(forms.ModelForm):
    class Meta:
        model = ThreatName
        fields = ['name', 'aka_name', 'references']

class ActorForm(forms.ModelForm):
    class Meta:
        model = ThreatActor
        fields = ['name', 'aka_name', 'source_country', 'references']

class VulnerabilityForm(forms.ModelForm):
    class Meta:
        model = Vulnerability
        fields = ['name', 'base_score', 'description', 'references']

class QueryAIAssistantForm(forms.Form):
    connector = forms.ModelChoiceField(
        queryset=Connector.objects.filter(domain='analytics', enabled=True),
        required=True
        )
    question = forms.CharField(widget=forms.Textarea(
        attrs={
            'class': 'question-ai-assistant',
            'placeholder': 'E.g., Detect network activity involving the rundll32.exe process.',
        }),
        required=True
    )

    def __init__(self, *args, selected_connector_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['connector'].initial = selected_connector_id
