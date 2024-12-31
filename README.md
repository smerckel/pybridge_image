PYBRIDGE_IMAGE  
==============

The program pybridge, available from https://sourceforge.net/projects/pybridge/, is a free online program to play 
the card game of contract bridge. Unfortunately, it seems not to be maintained anymore, and written in python2.7 
using the obselete gtk2 toolkit.

This little project allows you to build a podman image, so that both the server program and the client(s) can be 
run without problems on a modern Linux OS.

Installation
============
* Clone the repository
* Change directory into the newly created directory
* run the build.sh script

The build.sh script pulls a base image, based on ubuntu 18.04, installs the prerequisites of the pybridge program, copies
the pybridge source code, and installs the pybridge program. Two launch scripts are copied to ~/.local/bin, namely 
pybridge and pybridge-server.

Running pybridge
================
The pybridge program consists of a server program and requires four clients (the players). All clients should have access to the server program, 
which can be started as

`$ pybridge-server`

The pybridge server listens to port 5040 for incomming connections.

The clients are started as

`$ pybridge`

which offers a diagologue to connect to a server. 

See also the original site of pybridge https://sourceforge.net/projects/pybridge.

Author's note
=============
I have modified the original code to allow to play deals recorded in so-called pbn files. The internet hosts many files with hands that
have been played on international tournaments, for example. In this way, you can compare your play with the professionals.

Options
-------
-f <filename> : specifies the filename of a pbn file.

-s <int>      : stride with which each hand from the file is selected. Default 1. 

-d <int>      : start with deal n (default 0).

