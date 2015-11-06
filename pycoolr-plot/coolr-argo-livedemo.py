#!/usr/bin/env python

#
# matplot-based live demo tool, customized for the Argo demo
#
# Contact: Kaz Yoshii <ky@anl.gov>
#

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
fakemode=False

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
    print ''
    print '--fake: generate fakedata instead of querying'
    print ''

shortopt = "h"
longopt = ['output=','node=', 'cfg=', 'enclave=', 'fake' ]
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
#    elif o in ("--appcfg"):
#        appcfgfn=a
    elif o in ("--enclave"):
        enclave=a
    elif o in ("--fake"):
        fakemode=True

#
# load config files
#

with open(cfgfn) as f:
    cfg = json.load(f)

if len(targetnode) == 0 :
    targetnode = cfg['masternode']
    print 'Use %s as target node' % targetnode
if len(enclave) == 0:
    enclave = cfg['masternode']
    print 'Use %s as enclave' % enclave

#if len(appcfgfn) > 0:
#    with open(appcfgfn) as f:
#        appcfg = json.load(f)
#    for k in appcfg.keys():
#        cfg[k] = appcfg[k]

if fakemode:
    import fakedata
    targetnode='v.node'
    enclave = 'v.enclave'
    info = json.loads(fakedata.gen_info(targetnode))
else:
    info = querydataj("%s --info" % cfg['querycmd'])[0]

#
#
#
try:
    logf = open(outputfn, 'w', 0) # unbuffered write
except:
    print 'unable to open', outputfn

cmd = cfg['dbquerycmd'] # command to query the sqlite DB

lastdbid=0 # this is used to keep track the DB records
npkgs=info['npkgs']
lrlen=120  # to option
gxsec=lrlen # graph x-axis sec

#
#
#
params = {}  # graph params XXX: extend for multinode
params['cfg'] = cfg
params['info'] = info
params['lrlen'] = lrlen
params['gxsec'] = gxsec
params['cur'] = 0  # this will be updated
params['pkgcolors'] = [ 'blue', 'green' ] # for now
params['targetnode'] = targetnode

#
# Instantiate data list
#
# CUSTOM
#

enclave_lr = {}
enclave_lr['pkg'] = [listrotate2D(length=lrlen) for i in range(npkgs)]
enclave_lr['dram'] = [listrotate2D(length=lrlen) for i in range(npkgs)]

rapl_lr = {}
rapl_lr['pkg'] = [listrotate2D(length=lrlen) for i in range(npkgs)]
rapl_lr['dram'] = [listrotate2D(length=lrlen) for i in range(npkgs)]

temp_lr = [listrotate2D(length=lrlen) for i in range(npkgs)]
freq_lr = [listrotate2D(length=lrlen) for i in range(npkgs)]

#runtime_lr = listrotate2D(length=lrlen)
#appperf_lr = listrotate2D(length=lrlen)

modulelist = [] # a list of graph modules


#
# matplot related modules
#
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as manimation
matplotlib.rcParams.update({'font.size': 12})
from clr_matplot_graphs import *

fig = plt.figure( figsize=(18,10) )
fig.canvas.set_window_title('pycoolr live demo')

plt.ion()
plt.show()

class layoutclass:
    def __init__(self, row=2, col=4):
        self.row = row
        self.col = col
        self.idx = 1

    def getax(self):
        ax = plt.subplot(self.row, self.col, self.idx)
        self.idx += 1
        return ax

layout = layoutclass(2,5)

#
# CUSTOM
#
ax = layout.getax()
pl_enclave_rapl = plot_rapl(ax, params, enclave_lr['pkg'], enclave_lr['dram'], titlestr='Enclave: %s' % enclave)

ax = layout.getax()
pl_node_rapl = plot_rapl(ax, params, rapl_lr['pkg'], rapl_lr['dram'], titlestr="%s" % targetnode)

ax = layout.getax()
pl_node_temp = plot_line_err(ax, params, temp_lr)

ax = layout.getax()
pl_node_freq = plot_line_err(ax, params, freq_lr)


# register a new graph. XXX: move to command line
modnames = ['runtime', 'application']

for k in modnames:
    name='graph_%s' % k
    m = __import__(name)
    c = getattr(m, name)
    modulelist.append( c(params, layout) )

#ax = plt.subplot(row, col, idx)
#pl_runtime = plot_runtime(ax, params, runtime_lr) # , titlestr="%s" % targetnode)
#idx += 1

#ax = plt.subplot(row, col, idx)
#pl_appperf = plot_appperf(ax, params, appperf_lr) # , titlestr="%s" % targetnode)
#idx += 1


# ax = plt.subplot(row,col,idx)
# pl_info = plot_info(ax, params)
# idx += 1


fig.tight_layout()


params['ts'] = 0

while True:
    profile_t1 = time.time()

    if fakemode:
        j = fakedata.queryfakedataj()
    else:
        if lastdbid > 0:
            j = querydataj("%s --gtidx=%d" % (cmd, lastdbid))
        else:
            j = querydataj(cmd)
        if len(j) > 0:
            lastdbid = int(j[-1]['dbid'])

    profile_t2 = time.time()
    for e in j:
        # print e
        if not e.has_key('node'):
            continue

        if params['ts'] == 0:
            params['ts'] = e['time']
            t = 0

        # ENCLAVE Power 
        if e['node'] == enclave and e['sample'] == 'energy':
            t = e['time'] - params['ts']
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
            t = e['time'] - params['ts']
            params['cur'] = t # this is used in update()

            for pkgid in range(npkgs):
                tmppow = e['power']['p%d'%pkgid]
                tmplim = e['powercap']['p%d'%pkgid]
                tmppowdram =  e['power']['p%d/dram'%pkgid] * 0.25
                rapl_lr['pkg'][pkgid].add(t, tmppow, tmplim)
                rapl_lr['dram'][pkgid].add(t, tmppowdram)
            pl_node_rapl.update(params, rapl_lr['pkg'], rapl_lr['dram'])
        elif e['node'] == targetnode and e['sample'] == 'temp':
            t = e['time'] - params['ts']
            params['cur'] = t # this is used in update()
            for p in range(npkgs):
                v0 = e['p%d' % p]['mean']
                v1 = e['p%d' % p]['std']
                temp_lr[p].add(t,v0,v1)
            pl_node_temp.update(params, temp_lr)
        elif e['node'] == targetnode and e['sample'] == 'freq':
            t = e['time'] - params['ts']
            params['cur'] = t # this is used in update()
            for p in range(npkgs):
                v0 = e['p%d' % p]['mean']
                v1 = e['p%d' % p]['std']
                freq_lr[p].add(t,v0,v1)
            pl_node_freq.update(params, freq_lr, ptype = 'freq')
        else:
            for m in modulelist:
                m.update(params,e)

    plt.draw()

    profile_t3 = time.time()


    plt.pause(.5)

    profile_t4 = time.time()

    print 'Profile Time [S]: all=%.2lf (query:%.2lf draw:%.2lf misc:%.2lf)' %\
        (profile_t4-profile_t1, profile_t2-profile_t1,\
         profile_t3-profile_t2, profile_t4-profile_t3)

sys.exit(0)

