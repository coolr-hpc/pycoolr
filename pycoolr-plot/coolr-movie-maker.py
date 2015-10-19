#!/usr/bin/env python

#
# generate a mp4 movie file from specified json file
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

temp_data = frames.getlist(node,'temp')
# CUSTOMIZE
temp_plot_mean  = [listrotate2D(length=lrlen) for i in range(npkgs)]

#
#
#

FFMpegWriter = manimation.writers['ffmpeg']
writer = FFMpegWriter(fps=2, 
                      metadata=
                      dict(title='foo', artist='COOLR', comment='no comment'))


fig = plt.figure()

col = 1
row = 1
idx = 1
ax = plt.subplot(row,col,idx)
idx += 1
l = plot_temp(ax, params, temp_plot_mean)

fig.tight_layout()

print 'generating %d frames' % nframes
st = time.time()
with writer.saving(fig, "m.mp4", 100):
    for i in range(nframes):
        print 'frame:', i
        d = temp_data[i]
        if not d == None:
            for p in range(npkgs):
                t = d['time'] - ts
                v = d['p%d' % p]['mean']
                print p, t,v
                temp_plot_mean[p].add(t,v)
                params['cur'] = t
        l.update(params, temp_plot_mean)

        writer.grab_frame()

elapsed = time.time() - st

print 'elapsed: %3lf' % elapsed
print '%.3f sec/frame' %  (float(elapsed)/nframes)
