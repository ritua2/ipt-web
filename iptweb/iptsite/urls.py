from django.conf.urls import include, url
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import AddNews, DeleteNews
#News page added by Thomas Hilton Johnson III, for quick reference if there is a bug
urlpatterns = [
    url(r'^history$', views.history, name='history'),
    url(r'^run$', views.run, name='run'),
    url(r'^help$', views.help, name='help'),
#    url(r'^news$',views.news, name='news'),
    url(r'^compile$', views.compile, name='compile'),
    url(r'^terminal$', views.terminal, name='terminal'),
    url(r'^webterm$', views.webterm, name='webterm'),
    url(r'^login$', views.login, name='login'),
    url(r'^logout$', views.logout, name='logout'),
    url(r'^create_account$', views.create_account, name='create_account'),
    url(r'^accounts/', include('iptsite.accounts.urls', namespace='accounts')),
    url(r'^admin$', views.admin, name='admin'),
    url(r'^download/(?P<path>.*)/?$', views.download, name='download'),
    url(r'^upload?$', views.upload, name='upload'),
    url(r'^community/', include('messageBoard.urls')),
    url(r'^getdropdownvalues$', views.getdropdownvalues, name='getdropdownvalues'),
    url(r'^newsHistory$',views.newsHistory, name='newsHistory'),
    url(r'^postnews$', AddNews.as_view(), name='addnews'),
    url(r'removenews/(?P<pk>[0-9]+)/$', DeleteNews.as_view(), name='deletenews'),
    url(r'^$', views.login, name='login'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
