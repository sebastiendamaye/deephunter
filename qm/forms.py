from django import forms
from .models import Review, Analytic, SavedSearch

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
