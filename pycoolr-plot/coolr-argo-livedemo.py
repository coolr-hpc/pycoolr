#!/usr/bin/env python

import sys, os, re
import json
import time
import getopt

from listrotate import *
from clr_utils import *

cfgfn='chameleon-argo-demo.cfg'
appcfgfn='chameleon-app.cfg'
outputfn='multinodes.json'
targetnode=''
enclave=''

def usage():
    print ''
    print 'Usage: %s [options]' % sys.argv[0]
    print ''
    print '[options]'
    print ''
    print '--cfg fn : the main configuration (default: %s)' % cfgfn
    print '--outputfn fn : specify output fiflename (default: %s)' % outputfn
    print ''
    print '--enclave name : enclave node name'
    print '--node  name : target node the node power, temp, freq and app graphs'
    print '--appcfg fn : additional configuration for app graphs'
    print ''

shortopt = "h"
longopt = ['output=','node=', 'cfg=', 'appcfg=', 'enclave=' ]
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
    elif o in ("--node"):
        targetnode=a
    elif o in ("--cfg"):
        cfgfn=a
    elif o in ("--appcfg"):
        appcfgfn=a
    elif o in ("--enclave"):
        enclave=a


with open(cfgfn) as f:
    cfg = json.load(f)

if len(targetnode) == 0 :
    targetnode = cfg['masternode']
    print 'Use %s as target node' % targetnode


if len(appcfgfn) > 0:
    with open(appcfgfn) as f:
        appcfg = json.load(f)

    for k in appcfg.keys():
        cfg[k] = appcfg[k]


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

#
# instantiate data list
#
# CUSTOM

enclave_lr = {}
enclave_lr['pkg'] = [listrotate2D(length=lrlen) for i in range(npkgs)]
enclave_lr['dram'] = [listrotate2D(length=lrlen) for i in range(npkgs)]

node_lr = {}
node_lr['pkg'] = [listrotate2D(length=lrlen) for i in range(npkgs)]
node_lr['dram'] = [listrotate2D(length=lrlen) for i in range(npkgs)]


#
# matplot related modules
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
# CUSTOM
#
ax = plt.subplot(row, col, idx)
pl_enclave_rapl = plot_rapl(ax, params, enclave_lr['pkg'], enclave_lr['dram'], titlestr='Enclave')
idx += 1

ax = plt.subplot(row, col, idx)
pl_node_rapl = plot_rapl(ax, params, node_lr['pkg'], node_lr['dram'], titlestr="%s" % targetnode)
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
        if not e.has_key('node'):
            continue

        # ENCLAVE Power 
        if e['node'] == 'master' and e['sample'] == 'energy':
            if ts == 0:
                ts = e['time']
                t = 0
            else:
                t = e['time'] - ts

            params['cur'] = t # this is used in update()

            for pkgid in range(npkgs):
                tmppow = e['power']['p%d'%pkgid]
                tmplim = e['powercap']['p%d'%pkgid]
                tmppowdram =  e['power']['p%d/dram'%pkgid] * 0.25
                enclave_lr['pkg'][pkgid].add(t, tmppow, tmplim)
                enclave_lr['dram'][pkgid].add(t, tmppowdram)
            pl_enclave_rapl.update(params, enclave_lr['pkg'], enclave_lr['dram'])
        #
        # NODE Power
        elif e['node'] == targetnode and e['sample'] == 'energy':
            for pkgid in range(npkgs):
                tmppow = e['power']['p%d'%pkgid]
                tmplim = e['powercap']['p%d'%pkgid]
                tmppowdram =  e['power']['p%d/dram'%pkgid] * 0.25
                node_lr['pkg'][pkgid].add(t, tmppow, tmplim)
                node_lr['dram'][pkgid].add(t, tmppowdram)
            pl_node_rapl.update(params, enclave_lr['pkg'], enclave_lr['dram'])

    plt.draw()

    t3=time.time()

    if len(j) > 0:
        lastdbid = int(j[-1]['dbid'])

    time.sleep(1)
    t4=time.time()

    print 'Profile time: %.2lf %.2lf %.2lf %.2lf' % (t4-t1,  t2-t1, t3-t2, t4-t3)

sys.exit(0)

