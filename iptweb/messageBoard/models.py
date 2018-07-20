# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
class EntryQuerySet(models.QuerySet):
    def published(self):
        return self.filter(publish=True)

class Entry(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    tag = models.CharField(max_length=50,null=True)
    publish = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = EntryQuerySet.as_manager()

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Forum Entry"
        verbose_name_plural = "Forum Entries"
        ordering = ["-created"]

class Reply(models.Model):
    comment = models.TextField()
    parentEntry =  models.ForeignKey(Entry, related_name="commentParentEntry")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.parentEntry.title)

    class Meta:
	verbose_name_plural = "Forum Replies"
	ordering = ["-created"]
