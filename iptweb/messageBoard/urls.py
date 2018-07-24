from django.conf.urls import include, url
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import *
urlpatterns = [
    url(r'blog/$', views.commentHistory, name='commentHistory'),
    url(r'addreply/(?P<pk>[0-9]+)/$', ReplyPost.as_view(), name='replyforum'),
    url(r'quotereply/(?P<pk>[0-9]+)/(?P<cpk>[0-9]+)/$', ReplytoReply.as_view(), name='replycomment'),
    url(r'newdetail/$', NewPost.as_view(), name='newforum'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
