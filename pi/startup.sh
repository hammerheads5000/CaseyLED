#!/usr/bin/env bash
sleep 10
cd ~/CaseyLED/pi
./.venv/bin/python3 frontend.py > log.txt 2>&1
bash
