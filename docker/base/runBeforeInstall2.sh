#!/bin/bash

module unload intel/13.0.2.146
export JAVA_TOOL_OPTIONS="-Xms2G -Xmx2G"
#export JAVA_HOME=/usr/java/jdk1.7.0_45
export JAVA_HOME=/usr/java/jdk1.7.0_79/

#export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$JAVA:_HOME/jre/lib/amd64/server
export LD_LIBRARY_PATH=$JAVA_HOME/jre/lib/amd64/server

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/work/01698/rauta/fraspa/boost_1_47_0:/work/01698/rauta/fraspa/boost_1_47_0/bin.v2/libs:/work/01698/rauta/fraspa/rose/boost_install/include:/work/01698/rauta/fraspa/rose/boost_install/lib:/work/01698/rauta/fraspa/rose/roseCompileTree:/work/01698/rauta/fraspa/rose/roseCompileTree/lib

echo $LD_LIBRARY_PATH

