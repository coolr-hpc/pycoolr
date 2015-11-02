#!/usr/bin/env python

import sys, os, re
import json
import time
import getopt

from listrotate import *
from clr_utils import *

configfn='chameleon-argo-demo.cfg'
outputfn = 'multinodes.json'
nodes = []

def usage():
    print ''
    print 'Usage: coolr-live-multi.py [options] [config]'
    print ''
    print '[options]'
    print ''
    print '--outputfn fn: specify output fiflename (default:%s)' % outputfn
    print '--nodes nodes: list of the nodes. comma separated (default:allnodes)'
    print ''

shortopt = "h"
longopt = ['output=','nodes=']
try:
    opts, args = getopt.getopt(sys.argv[1:],
                               shortopt, longopt)
except getopt.GetoptError, err:
    print err
    usage()
    sys.exit(1)

for o, a in opts:
    if o in ('-h'):
        usage()
        sys.exit(0)
    elif o in ("--output"):
        outputfn=a
    elif o in ("--nodes"):
        nodes=a.split(',')

if len(args) > 0:
    configfn=args[0]

with open(configfn) as f:
    cfg = json.load(f)





nodes.append(cfg['masternode'])

try:
    logf = open(outputfn, 'w', 0) # unbuffered write
except:
    print 'unable to open', outputfn

lastdbid=0
cmd=cfg['dbquerycmd']

fps=1 # dummy
lrlen=120  # to option
gxsec = lrlen * (1.0/fps) # graph x-axis sec

npkgs=2 # hardcode for now

allnodes={}  # power data for now

for n in nodes:
    allnodes[n] = {}
#    allnodes[n]['total'] = listrotate2D(length=lrlen)
    allnodes[n]['pkg'] = [listrotate2D(length=lrlen) for i in range(npkgs)]
    allnodes[n]['dram'] = [listrotate2D(length=lrlen) for i in range(npkgs)]


#
#
#
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as manimation
matplotlib.rcParams.update({'font.size': 12})
from clr_matplot_graphs import *

fig = plt.figure( figsize=(15,10) )

plt.ion()
plt.show()

params = {}  # graph params XXX: extend for multinode
params['cfg'] = cfg
#params['info'] = info
params['gxsec'] = gxsec
params['cur'] = 0  # this will be updated
params['pkgcolors'] = [ 'blue', 'green' ] # for now

col = 2
row = 2
idx = 1
#
pl_rapl = {}
for n in nodes:
    ax = plt.subplot(row,col,idx)
    # XXX: may cause runtime error
    pl_rapl[n] = plot_rapl(ax, params, allnodes[n]['pkg'], allnodes[n]['dram'], nodename=n)
    idx += 1


ts = 0

while True:
    t1=time.time()
    if lastdbid > 0:
        j = querydataj("%s --gtidx=%d" % (cmd, lastdbid))
    else:
        j = querydataj(cmd)

    t2=time.time()
    for e in j:
        # print e
        if e.has_key('node'):
            if e['sample'] != 'energy':
                print 'skip:', e['sample']
                continue
            node = e['node']

            if not node in nodes:
                continue

            if ts == 0:
                ts = e['time']
                t = 0
            else:
                t = e['time'] - ts

            params['cur'] = t # this is used in update()

            for pkgid in range(npkgs):
                allnodes[node]['pkg'][pkgid].add(t, e['power']['p%d'%pkgid],\
                                                     e['powercap']['p%d'%pkgid])
                allnodes[node]['dram'][pkgid].add(t, e['power']['p%d/dram'%pkgid])
            pl_rapl[node].update(params, allnodes[node]['pkg'], \
                                  allnodes[node]['dram'])


    plt.draw()

    t3=time.time()

    if len(j) > 0:
        lastdbid = int(j[-1]['dbid'])

    time.sleep(1)
    t4=time.time()

    print 'Profile time: %.2lf %.2lf %.2lf %.2lf' % (t4-t1,  t2-t1, t3-t2, t4-t3)


sys.exit(0)

