#!/bin/bash
podman build -t pybridge .
cp pybridge ~/.local/bin
cp pybridge-server ~/.local/bin
