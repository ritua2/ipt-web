from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^history$', views.history, name='history'),
    url(r'^run$', views.run, name='run'),
    url(r'^help$', views.help, name='help'),
    url(r'^compile$', views.compile, name='compile'),
    url(r'^terminal$', views.terminal, name='terminal'),
    url(r'^login$', views.login, name='login'),
    url(r'^logout$', views.logout, name='logout'),
    url(r'^create_account$', views.create_account, name='create_account'),
]
