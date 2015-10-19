#!/usr/bin/env python

#
# generate a mp4 movie file from specified json file
#
# This tool and its config file are not flexible.
# I marked a customizable point as 'CUSTOMIZE'
#
#
#
#
# Kazutomo Yoshii <ky@anl.gov>
# 

import time, sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as manimation
from clr_matplot_graphs import *

from genframes import *
from listrotate import *

#
#

# XXX: add these to the option later
fps = 1
lrlen = 120  # this is for listrotate. the size of array
gxsec = lrlen * (1.0/fps) # graph x-axis sec
dpi = 160  # for writer.saving(). is this actually dpi, btw?
outputfn = 'm.mp4'


#

if len(sys.argv) < 3:
    print 'Usage: %s config data' % sys.argv[0]
    sys.exit(1)

print 'Config: ', sys.argv[1]
print 'Data: ', sys.argv[2]
    
with open(sys.argv[1]) as f:
    cfg = json.load(f)
frames = genframes(sys.argv[2])
# XXX: single node target now
node = frames.getnodes()[0]
info = frames.info[node]
npkgs = info['npkgs']
ncpus = info['ncpus']

#
# 
frames.setfps(fps)
nframes = frames.nframes % 100 # just for debugging
ts = frames.ts  # the start time

#
# data set
#
params = {}  # graph params
params['cfg'] = cfg
params['gxsec'] = gxsec
params['cur'] = ts  # this will be updated
params['pkgcolors'] = [ 'blue', 'green' ] # for now

temp_data = frames.getlist(node,'temp')
freq_data = frames.getlist(node,'freq')
energy_data = frames.getlist(node,'energy')

# CUSTOMIZE when need more details
temp_lr = [listrotate2D(length=lrlen) for i in range(npkgs)]
freq_lr = [listrotate2D(length=lrlen) for i in range(npkgs)]

#
#
#

FFMpegWriter = manimation.writers['ffmpeg']
writer = FFMpegWriter(fps=2, 
                      metadata=
                      dict(title='foo', artist='COOLR', comment='no comment'))


fig = plt.figure()

# CUSTOMIZE
col = 2
row = 1
idx = 1
ax = plt.subplot(row,col,idx)
idx += 1
pl_temp = plot_line_err(ax, params, temp_lr)
ax = plt.subplot(row,col,idx)
idx += 1
pl_freq = plot_line_err(ax, params, freq_lr, ptype = 'freq' )

fig.tight_layout()

print 'Generating %s with %d frames ...' % (outputfn, nframes)
st = time.time()
with writer.saving(fig, outputfn, dpi):
    for i in range(nframes):
        print 'frame:%04d/%04d / %5.1lf %%' % (i,nframes, (100.*i/nframes))
        #
        # CUSTOMIZE
        #
        tempd = temp_data[i]
        freqd = freq_data[i]
        
        if not tempd == None:
            for p in range(npkgs):
                t = tempd['time'] - ts
                params['cur'] = t # this is used in update()
                v0 = tempd['p%d' % p]['mean']
                v1 = tempd['p%d' % p]['std']
                temp_lr[p].add(t,v0,v1)
        pl_temp.update(params, temp_lr)
                
        if not freqd == None:
            for p in range(npkgs):
                t = freqd['time'] - ts
                params['cur'] = t
                v0 = freqd['p%d' % p]['mean']
                v1 = freqd['p%d' % p]['std']
                freq_lr[p].add(t,v0,v1)

        pl_freq.update(params, freq_lr, ptype = 'freq')

        #
        #
        writer.grab_frame()

elapsed = time.time() - st

print 'elapsed: %3lf' % elapsed
print '%.3f sec/frame' %  (float(elapsed)/nframes)
print 'done'
