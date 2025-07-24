from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        exclude = ['analytic', 'reviewer']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 2}),
        }

    
    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        comments = cleaned_data.get('comments')
        if decision == 'PENDING' and not comments:
            self.add_error('comments', 'Comments are required when decision is "Need to be updated".')
        return cleaned_data
    