FROM ubuntu:18.04 
RUN apt-get update
RUN apt-get install -y python 
RUN apt-get install -y python-pip 
RUN apt-get install -y python-gtk2
RUN apt-get install -y python-glade2 
RUN apt-get install -y python-sqlobject
RUN apt-get install -y python-twisted
RUN apt-get install -y socat
RUN pip install configobj
COPY ./src /src
RUN cd /src && pip install .
RUN mkdir /root/.pybridge
COPY ./config/* /root/.pybridge
COPY ./bin/* /usr/local/bin
#ENTRYPOINT /usr/local/bin/pybridge
#ENTRYPOINT /usr/local/bin/pybridge-server
