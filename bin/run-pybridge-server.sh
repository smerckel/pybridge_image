#!/bin/bash

# use socat to redirect tcp traffic from port 5041 to 5040 because for
# some reason pybridge-server does not bind well to port 5040.
socat TCP-LISTEN:5041,fork TCP:127.0.0.1:5040 &

# change dir to the directory where the local directory is mounted:
cd /root/pbn

# start pybride-server
pybridge-server $@
