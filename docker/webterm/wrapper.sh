#!/bin/bash
# wrapper script to launch the webterm container and read the port.
# Requires the ssl files to be in a directory called "ssl" in the deployment path for this file.
#
# Parameters:
#   $1: name for the container
#   $2: path on the host for the data to be mounted (mounted at /data in the container).
#
# Example call:
#   $ ./wrapper.sh dev.ipt.jstubbs /data/ipt/storage/jstubbs


# requires the name to be passed as the first argument
name=$1

# requires the data mount (posix path) to be passed as a second argument
data=$2

# launch the container
docker run --name $1 -p 3000 -dt -v $data:/data -v $(pwd)/ssl:/ssl jstubbs/ipt-webterm app.js --sslkey /ssl/ipt-web.tacc.utexas.edu.key --sslcert /ssl/ipt-web.tacc.utexas.edu.bundle.crt -p 3000

# get the container id by first grep'ing for the name (which should be a unique container) and then
# pulling the first container
cid="$(docker ps | grep $name | awk ' { print $1 } ')"

# write out the port mappings for the container
docker port $cid
