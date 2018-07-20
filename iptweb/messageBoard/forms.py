from django.forms.models import ModelForm
from .models import *
from django import forms

class EntryForm(ModelForm):
    class Meta:
        model = Entry
        exclude = ('',)


class ReplyForm(ModelForm):
    class Meta:
        model = Reply
        exclude = ('parentEntry',)

