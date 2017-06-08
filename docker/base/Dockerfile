# Image: ipt-min

from centos:7

RUN yum install -y which git wget flex bison make java java-1.8.0-openjdk-devel gcc gcc-gfortran c++ autoconf-2.69-11.el7.noarch automake-1.13.4-3.el7.noarch libtool-2.4.2-21.el7_2.x86_64

RUN mkdir -p /boost_install

ADD boost_1_47_0.tar.gz /boost_1_47_0.tar.gz

RUN git clone https://github.com/rose-compiler/rose-develop rose


ADD rose-0.9.5a-without-EDG-20584.tar.gz /rose-0.9.5a-without-EDG-20584.tar.gz

RUN mkdir /roseCompileTree

ADD install_boost_and_rose.sh /install_boost_and_rose.sh

RUN chmod +x /install_boost_and_rose.sh

RUN sh install_boost_and_rose.sh

