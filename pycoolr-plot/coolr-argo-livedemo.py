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

# default values

modnames = ['runtime', 'application', 'power', 'temp', 'freq', 'enclave']
cfgfn='chameleon-argo-demo.cfg'
appcfgfn='chameleon-app.cfg'
outputfn='multinodes.json'
targetnode=''
enclave=''
fakemode=False
figwidth=20
figheight=12
ncols=4
nrows=3

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
    print '--width=int  : the width of the entire figure (default: %d)' % figwidth
    print '--height=int : the height of the entire figure (default: %d)' % figheight
    print ''
    print '--ncols : the number of columns (default: %s)' % ncols
    print '--nrows : the number of rows (default: %s)' % nrows
    print ''
    print '--fake: generate fakedata instead of querying'
    print ''
    print '--list : list available graph module names'
    print '--mods=CSV : specify a list of graph modules using comma separated values'
    print ''

shortopt = "h"
longopt = ['output=','node=', 'cfg=', 'enclave=', 'fake', 'width=', 'height=', 'list', 'mods=', 'ncols=', 'nrows=' ]
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
    elif o in ("--enclave"):
        enclave=a
    elif o in ("--fake"):
        fakemode=True
    elif o in ("--width"):
        figwidth=int(a)
    elif o in ("--height"):
        figheight=int(a)
    elif o in ("--nrows"):
        nrows=int(a)
    elif o in ("--ncols"):
        ncols=int(a)
    elif o in ("--list"):
        print ''
        print '[available graph modules]'
        print ''
        for i in modnames:
            print i
        print ''
        print ''
        sys.exit(0)
    elif o in ("--mods"):
        modnames = a.split(",")

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
params['outputfn'] = outputfn
params['cfg'] = cfg
params['info'] = info
params['lrlen'] = lrlen
params['gxsec'] = gxsec
params['cur'] = 0  # this will be updated
params['pkgcolors'] = [ 'blue', 'green' ] # for now
params['targetnode'] = targetnode
params['enclave'] = enclave


#
# matplot related modules
#
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as manimation
matplotlib.rcParams.update({'font.size': 12})
from clr_matplot_graphs import *

fig = plt.figure( figsize=(figwidth,figheight) )
fig.canvas.set_window_title('COOLR live demo tool')

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

layout = layoutclass(nrows, ncols)

#
# register  new graph modules
#
#

modulelist = [] # a list of graph modules

for k in modnames:
    name='graph_%s' % k
    m = __import__(name)
    c = getattr(m, name)
    modulelist.append( c(params, layout) )

fig.tight_layout(pad=2.0) # w_pad=1.0, h_pad=2.0

#
#
#

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

        for m in modulelist:
            m.update(params,e)

    plt.draw()

    profile_t3 = time.time()

    # plt.pause(.5)

    profile_t4 = time.time()

    print 'Profile Time [S]: all=%.2lf (query:%.2lf draw:%.2lf misc:%.2lf)' %\
        (profile_t4-profile_t1, profile_t2-profile_t1,\
         profile_t3-profile_t2, profile_t4-profile_t3)

sys.exit(0)
