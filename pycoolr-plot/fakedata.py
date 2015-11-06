#!/usr/bin/env python

import os, sys, re, time
import numpy as np
import subprocess
import random as r
import json

def gen_info():
    buf = '{"nodeinfo":"frontend","kernelversion":"4.1.3-argo","cpumodel":63,"memoryKB":131787416,"freqdriver":"pstate","samples":["temp","energy","freq"],"ncpus":48,"npkgs":2,"pkg0":[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46],"pkg1":[1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47],"pkg0phyid":[0,1,2,3,4,5,8,9,10,11,12,13,0,1,2,3,4,5,8,9,10,11,12,13],"pkg1phyid":[0,1,2,3,4,5,8,9,10,11,12,13,0,1,2,3,4,5,8,9,10,11,12,13],"nnodes":2,"node1":[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46],"node1":[1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47],"max_energy_uj":{"p0":262143328850,"p1":262143328850}}'
    return buf

def gen_argobots():
    n = 20
    t = time.time()
    buf  = '{'
    buf += '"time":%lf,' % t
    buf += '"node":"frontend",'
    buf += '"sample":"argobots",'
    buf += '"num_es":%d,' % n
    buf += '"num_threads":{'
    for i in range(0,n-1):
        buf += '"es%d":%lf,' % (i, r.random()*100)
    buf += '"es%d":%lf},' % (n-1, r.random()*100)
    buf += '"num_tasks":{'
    for i in range(0,n-1):
        buf += '"es%d":%lf,' % (i, r.random()*100)
    buf += '"es%d":%lf}}' % (n-1, r.random()*100)
    return buf

def gen_application():
    t = time.time()
    buf  = '{'
    buf += '"time":%lf,' % t
    buf += '"node":"frontend",'
    buf += '"sample":"application",'
    buf += '"#TE_per_sec_per_node":%lf,' %  (r.random() * 10000000.0)
    buf += '"#TE_per_watt_per_node":%lf,' %  (r.random() * 10000000.0)
    buf += '"#TE_per_sec":%lf}' %  (r.random() * 10000000.0)
    return buf

def queryfakedataj():
    ret = []
    ret.append( json.loads(gen_info()) )
    ret.append( json.loads(gen_argobots()) )
    ret.append( json.loads(gen_application()) )
    return ret

if __name__ == '__main__':
    print
    print json.loads(gen_info())
    print
    print json.loads(gen_argobots())
    print
    print json.loads(gen_application())
    print
