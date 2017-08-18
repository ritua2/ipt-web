# Image: jstubbs/ipt-actor
# The actor used to launch IPT terminals from the web application.
from abacosamples/base-ubu

ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

ADD actor.py /actor.py

CMD ["python", "/actor.py"]