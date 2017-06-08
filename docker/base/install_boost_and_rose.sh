#!/bib/bash

export JAVA_HOME=/etc/alternatives/jre_openjdk; export JAVA_TOOL_OPTIONS="-Xms2G -Xmx2G"
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/etc/alternatives/jre/lib/amd64/server/

# install boost
cd /boost_1_47_0.tar.gz/boost_1_47_0
./bootstrap.sh --prefix=/boost_install
./b2 install --prefix=/boost_install

# install rose
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/boost_1_47_0.tar.gz/boost_1_47_0:/boost_1_47_0.tar.gz/boost_1_47_0/bin.v2/libs:/boost_install/lib:/boost_1_47_0.tar.gz/boost_1_47_0/include

# fix am__api_version in rose configure script
sed -i.bak "s/am__api_version=\"1.9\"/am__api_version=\"1.13\"/" /rose-0.9.5a-without-EDG-20584.tar.gz/rose-0.9.5a-20584/configure

export JAVA_HOME=/usr
/rose-0.9.5a-without-EDG-20584.tar.gz/rose-0.9.5a-20584/configure --prefix=/roseCompileTree --with-boost=/boost_install

#cd /roseCompileTree
#make -j 8
#make install
