# iptsite/forms.py

from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.forms.models import ModelForm
from messageBoard.models import Newscollection

# If you don't do this you cannot use Bootstrap CSS
class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username", max_length=30,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'username'}))
    password = forms.CharField(label="Password", max_length=30,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'password'}))

class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50)
    file = forms.FileField()

class NewsForm(ModelForm):
    class Meta:
        model = Newscollection
        exclude = ('',)
