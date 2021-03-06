# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http.response import HttpResponse, HttpResponseRedirect
from .models import *

from django.views.generic.edit import UpdateView, DeleteView, CreateView
from .forms import *
from django.core.urlresolvers import reverse
from django.conf import settings
# Create your views here.

def is_admin(user_name):
    return user_name in settings.ADMIN_USERS

def commentHistory(request):
    """
    This view generates the Job history page.
    """
    user_name = request.session.get("username")
    
    if request.method == 'GET':
        p = Entry.objects.all()
        context = {
            "admin": is_admin(user_name),
            "loggedinusername": user_name,
            'forum': p
        }
        return render(request, 'detail.html', context)

class NewPost(CreateView):
    form_class = EntryForm
    model = Entry
    template_name = 'customForm.html/'

    def get_success_url(self):
        print("hi")
        return reverse('history')

class ReplyPost(CreateView):
    form_class = ReplyForm
    model = Reply
    template_name = 'customForm.html/'

    def post(self,request,pk):
        form = self.form_class(request.POST)
        if form.is_valid():
           rep = form.save(commit=False)
           rep.parentEntry = Entry.objects.get(pk=pk)
           rep.save()
           return HttpResponseRedirect('/community/blog/')

class ReplytoReply(CreateView):
    form_class = ReplyForm
    model = Reply
    template_name = 'customForm.html/'

    #def get(self,request,pk,cpk):
     #   form = self.form_class(request.POST)
      #  form.fields["comment"]=Reply.objects.get(pk=cpk).comment
       # print(Reply.objects.get(pk=cpk).comment)
       # return render(request, self.template_name, {'form': form})
    def post(self,request,pk,cpk):
        form = self.form_class(request.POST)
        if form.is_valid():
           rep = form.save(commit=False)
	print(rep.comment)
        rep.comment ='Replied to:"'+ Reply.objects.get(pk=cpk).comment+'"......'+rep.comment
        rep.parentEntry = Entry.objects.get(pk=pk)
        rep.save()
        return HttpResponseRedirect('/community/blog/')
