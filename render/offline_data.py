#!/usr/bin/env python

#
# 
#

import os, sys, time, re
import json

class offline_data:

    def __init__(self,fn):
        self.read_coolr(fn)

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

    odata = offline_data("testdata/dgemmtest-coolrs.json")


    print odata.npkgs

        

