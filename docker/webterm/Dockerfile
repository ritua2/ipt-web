# Image: jstubbs/ipt-webterm
# Terminal with the IPT binary exposed over HTTPS. Launch with:
#     $ docker run --name term -p 3000 -dt jstubbs/ipt-webterm
# to use the default self-signed certs or:
#     $ docker run --name term -p 3000 -dt -v $(pwd)/ssl:/ssl jstubbs/ipt-webterm app.js --sslkey /ssl/ipt-web.tacc.utexas.edu.key --sslcert /ssl/ipt-web.tacc.utexas.edu.bundle.crt -p 3000
# The terminal will be available over SSH on the mapped port. Login with term/term

# Example run for local dev to mimic actor execution:
# docker run --name jstubbs.dev.IPT -p 3000 -dt -v $(pwd)/docker/nginx/ssl:/ssl jstubbs/ipt-webterm /app/app.js --urlPath /test --sslkey /ssl/ipt-web.tacc.utexas.edu.key --sslcert /ssl/ipt-web.tacc.utexas.edu.bundle.crt -p 3000

from krishnasrinivas/wetty

ADD cert.pem /app/cert.pem
ADD key.pem /app/key.pem
ADD app.js /app/app.js
ADD public/index.html /app/public/wetty/index.html
ADD public/index.html /app/public/index.html
ADD public/wetty.js /app/public/wetty/wetty.js

ADD ipt /ipt/ipt
WORKDIR /ipt

CMD ["/app/app.js", "--sslkey", "key.pem", "--sslcert", "cert.pem", "-p", "3000"]