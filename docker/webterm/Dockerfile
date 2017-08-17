# Image: jstubbs/ipt-webterm
# Terminal with the IPT binary exposed over HTTPS. Launch with:
#     $ docker run --name term -p 3000 -dt jstubbs/ipt-webterm
# The terminal will be available over SSH on the mapped port. Login with term/term

from krishnasrinivas/wetty

ADD cert.pem /app/cert.pem
ADD key.pem /app/key.pem
ADD ipt /ipt

CMD ["app.js", "--sslkey", "key.pem", "--sslcert", "cert.pem", "-p", "3000"]