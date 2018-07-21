from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^register$', views.register, name='register'),
    url(r'^authentication/$', views.manage_authentication, name='manage_authentication'),
    url(r'^register/$', views.register, name='register'),
    url(r'^registration-successful/$', views.registration_successful, name='registration_successful'),
    url(r'^password-reset/(?:(?P<code>.+)/)?$', views.password_reset, name='password_reset'),
    url(r'^activate/(?:(?P<code>.+)/)?$', views.email_confirmation, name='email_confirmation'),
    # url(r'^departments\.json$', views.departments_json, name='departments_json'),
]
