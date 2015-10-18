#!/usr/bin/env python

#
# Reconstructing graph from recorded data
#
# Where can I get?
# - a list of machines
# - a list of sample targets
# 

import os, sys, time, re
import json

class reconstruct:

    def __init__(self,fn):
        self.fn = fn




    def read_coolr(self,fn):
        with open(fn, 'r') as f:
            # assume the first line is info
            l = f.readline()
            self.info = json.loads(l)
            self.npkgs = self.info["npkgs"]
            self.temp = []
            self.energy
            while True:

if __name__ == "__main__":

    odata = offline_data("data/log")


    print odata.npkgs

        

