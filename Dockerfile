# Image: jstubbs/ipt-web
# Description: The Django web application for IPT.

FROM buildpack-deps:trusty

MAINTAINER Joe Stubbs <jstubbs@tacc.utexas.edu>

EXPOSE 8000

ENV DEBIAN_FRONTEND noninteractive
ENV TERM xterm

RUN apt-get update && \
    apt-get upgrade -y && \
    curl -sL https://deb.nodesource.com/setup_4.x | bash - && \
    apt-get install -y build-essential python python-dev gettext nodejs xvfb chromium-browser ruby-sass uwsgi && \
    curl -SL 'https://bootstrap.pypa.io/get-pip.py' | python

RUN pip install --upgrade pip && pip install uwsgi uwsgitop

RUN mkdir -p /opt/uwsgi && \
    curl -SLk -o /opt/uwsgi/uwsgi-2.0.15.tar.gz https://projects.unbit.it/downloads/uwsgi-2.0.15.tar.gz && \
    tar -xvzf /opt/uwsgi/uwsgi-2.0.15.tar.gz -C /opt/uwsgi && \
    uwsgi --build-plugin /opt/uwsgi/uwsgi-2.0.15/plugins/zabbix && \
    mkdir -p /usr/lib/uwsgi/plugins && \
    mv zabbix_plugin.so /usr/lib/uwsgi/plugins/.

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

COPY iptweb /iptweb

WORKDIR /iptweb

RUN python manage.py collectstatic --noinput

CMD ["/usr/local/bin/uwsgi", "--ini", "/iptweb/conf/uwsgi.ini"]