from django import forms

class NewJobForm(forms.Form):
    query = forms.CharField(label="Query (e.g., recon example.com)", max_length=512)
