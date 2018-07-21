#!/bin/bash
# wrapper script to launch the webterm container and read the port.
# Requires the ssl files to be in a directory called "ssl" in the deployment path for this file.
#

# requires the name to be passed as the first argument
name=$1

# requires the data mount (posix path) to be passed as a second argument
data=$2

# requires user token for wetty to be passed as a third argument
password=$3

# launch the container
docker service create --name $name --user 809892:818565 --replicas 1 --mount source=$data,target=/home/ipt,type=bind --mount source=/root/ssl,target=/ssl,type=bind --publish 3000 taccsciapps/ipt-webterm:dev $password

# get the port by first getting the service by name and then grep'ing for the PublishedPort
# which should be in the second column.
sleep 2
port="$(docker service inspect $name|grep PublishedPort| awk ' { print substr($2, 1, length($2)-1) } ')"

# write out the port mappings for the container
echo $port
