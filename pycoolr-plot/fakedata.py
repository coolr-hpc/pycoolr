#!/usr/bin/env python

import os, sys, re, time
import numpy as np
import subprocess
import random as r
import json

def gen_info(node):
    buf = '{"nodeinfo":"%s","kernelversion":"4.1.3-argo","cpumodel":63,"memoryKB":131787416,"freqdriver":"pstate","samples":["temp","energy","freq"],"ncpus":48,"npkgs":2,"pkg0":[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46],"pkg1":[1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47],"pkg0phyid":[0,1,2,3,4,5,8,9,10,11,12,13,0,1,2,3,4,5,8,9,10,11,12,13],"pkg1phyid":[0,1,2,3,4,5,8,9,10,11,12,13,0,1,2,3,4,5,8,9,10,11,12,13],"nnodes":2,"node1":[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46],"node1":[1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47],"max_energy_uj":{"p0":262143328850,"p1":262143328850}}' % node
    return buf

def gen_argobots(node):
    n = 20
    t = time.time()
    buf  = '{'
    buf += '"time":%lf,' % t
    buf += '"node":"%s",' % node
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

def gen_application(node):
    t = time.time()
    buf  = '{'
    buf += '"time":%lf,' % t
    buf += '"node":"%s",' % node
    buf += '"sample":"application",'
    buf += '"#TE_per_sec_per_node":%lf,' %  (r.random() * 100000.0)
    buf += '"#TE_per_watt_per_node":%lf,' %  (r.random() * 100000.0)
    buf += '"#TE_per_sec":%lf}' %  (r.random() * 100000.0)
    return buf

def gen_rapl(node):
    t = time.time()
    buf  = '{'
    buf += '"node":"%s",' % node
    buf += '"sample":"energy",'
    buf += '"time":%lf,' % t
    buf += '"powercap":{"p0":120.0,"p1":120.0,"p0/dram":0.0,"p1/dram":0.0},'
    p1=r.random()*120.0
    p2=r.random()*120.0
    p1d=r.random()*20.0
    p2d=r.random()*20.0
    buf += '"power":{"total":%.1lf,"p0":%.1lf,"p1":%.1lf,"p0/dram":%.1lf,"p1/dram":%.1lf}}' %\
           (p1+p2, p1, p2, p1d, p2d)

    # "energy": {"p0": 34, "p1": 34, "p0/dram": 25, "p1/dram": 25},
    return buf

def gen_mean_std(node,sample):
    t = time.time()
    buf  = '{'
    buf += '"node":"%s",' % node
    buf += '"sample":"%s",' % sample
    buf += '"time":%lf,' % t
    buf += '"p0":{"mean":%lf,"std":%lf},' % (r.random()*(30+40), r.random()*7)
    buf += '"p1":{"mean":%lf,"std":%lf}}' % (r.random()*(30+50), r.random()*5)

    return buf

def queryfakedataj():
    node="v.node"
    enclave="v.enclave"
    ret = []
    ret.append( json.loads(gen_info(node)) )
    ret.append( json.loads(gen_rapl(enclave)) )

    ret.append( json.loads(gen_rapl(node)) )
    ret.append( json.loads(gen_mean_std(node,"temp")) )
    ret.append( json.loads(gen_mean_std(node,"freq")) )

    ret.append( json.loads(gen_argobots(node)) )
    ret.append( json.loads(gen_application(node)) )

    return ret

if __name__ == '__main__':
    node="v.node"
    print
    print json.loads(gen_info(node))
    print
    print json.loads(gen_argobots(node))
    print
    print json.loads(gen_application(node))
    print
    print json.loads(gen_rapl(node))
    print
    print json.loads(gen_mean_std(node, "temp"))
    print
