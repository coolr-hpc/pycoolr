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
import numpy as np

class reconstruct:

    def __init__(self, cfgfn, jsonfn):
        with open(cfgfn) as f:
            self.cfg = json.load(f)

        # key is nodename
        self.info = {}
        self.data = {}

        # load all lines at init (naive)
        with open(jsonfn) as f:
            while True:
                l = f.readline()
                if not l:
                    break
                j = json.loads(l)
                if j.has_key("nodeinfo"):
                    # one info per node, otherwise unknown
                    self.info[j["nodeinfo"]] = j
                elif j.has_key("sample"):
                    nname = j["node"]
                    stype = j["sample"]

                    if not self.data.has_key(nname) :
                        self.data[nname] = {}
                    if not self.data[nname].has_key(stype) :
                        self.data[nname][stype] = []
                    self.data[nname][stype].append(j)
        # double check info's keys and data's keys match
        for k in sorted(self.info.keys()):
            if not self.data.has_key(k):
                raise KeyError

    def gettimerange(self):
        t0 = []
        t1 = []
        for k in self.data.keys():
            for k2 in self.data[k].keys():
                a = self.data[k][k2]
                t0.append(a[0]["time"])
                t1.append(a[-1]["time"])
        return np.max(t0), np.min(t1)

    def getnodes(self):
        n = []
        for k in self.data.keys():
            n.append(k)
        return n

    def getsamples(self,nname):
        s = []
        for k in self.data[nname].keys():
            s.append(k)
        return s

if __name__ == "__main__":

    r = reconstruct("chameleon.cfg", "chameleon.json" )

    nodes = r.getnodes()
    print nodes
    samples = r.getsamples(nodes[0])
    print samples
    t1,t2 = r.gettimerange()


        

