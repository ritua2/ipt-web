# Image: taccsciapps/ipt-webterm
# Description: This image adds the IPT binary to the wetty JavaScript web terminal for the IPT on the Web project.
# In order to build this image you must include the IPT software depenedencies - specifically the roseCompile
# directory.
#
# Instructions for how to create the roseCompile directory will be stored in the IPT wiki:
#
#
# Terminal with the IPT binary exposed over HTTPS. Launch with:
#     $ docker run --name term -p 3000 -dt taccsciapps/ipt-webterm
# to use the default self-signed certs or:
#     $ docker run --name term --user 809892:818565 -p 3000 -dt -v $(pwd)/ssl:/ssl taccsciapps/ipt-webterm app.js --sslkey /ssl/ipt-web.tacc.utexas.edu.key --sslcert /ssl/ipt-web.tacc.utexas.edu.bundle.crt -p 3000
# The terminal will be available over SSH on the mapped port. Login with term/term

# Example run for local dev to mimic actor execution:
# docker run --name jstubbs-dev-IPT -p 3000 -dt -v $(pwd)/docker/nginx/ssl:/ssl taccsciapps/ipt-webterm /app/app.js --urlPath /test --sslkey /ssl/ipt-web.tacc.utexas.edu.key --sslcert /ssl/ipt-web.tacc.utexas.edu.bundle.crt -p 3000

from krishnasrinivas/wetty

ADD cert.pem /app/cert.pem
ADD key.pem /app/key.pem
ADD app.js /app/app.js
ADD public/index.html /app/public/wetty/index.html
ADD public/index.html /app/public/index.html
ADD public/wetty.js /app/public/wetty/wetty.js

# add the ipt user and group
RUN groupadd --gid 818565 G-818565 && \
    useradd --uid 809892 --gid 818565 --create-home --shell /bin/bash ipt

#Add IPT software dependencies

ADD roseCompile /root/roseCompile

RUN apt-get update && apt-get install -y g++-multilib && \
    cp -r /usr/lib/gcc/x86_64-linux-gnu/4.9.2/include/* /usr/include/.
ADD roseCompile/ipt/src/rose_edg_required_macros_and_functions.h /usr/include/.
ADD roseCompile/runMe.sh /usr/include/.

RUN chmod -R 777 /root && \
    chown -R ipt:G-818565 /home/ipt && \
    chmod -R 777 /app/public

USER ipt

ENV JAVA_HOME /root/roseCompile/jdk1.8.0_131
ENV JAVA_TOOL_OPTIONS "-Xms2G -Xmx2G"
ENV PATH "/usr/include:/usr/lib/gcc/x86_64-linux-gnu/4.9.2/include:/root/roseCompile/lib/bin:/root/roseCompile/ipt/src:$PATH"
ENV LD_LIBRARY_PATH /usr/lib/gcc/x86_64-linux-gnu/4.9/libstdc++.a:/root/roseCompile/jdk1.8.0_131/jre/lib/amd64/server

WORKDIR /home/ipt

ADD entry.sh /usr/local/bin/entry.sh

ENTRYPOINT ["/usr/local/bin/entry.sh"]
