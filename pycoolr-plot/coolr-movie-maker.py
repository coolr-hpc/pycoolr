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
fps = 4 
lrlen = 120
outputfn = 'm.mp4'

#

if len(sys.argv) < 2:
    print 'Usage: %s json' % sys.argv[0]
    sys.exit(1)


frames = genframes(sys.argv[1])
# XXX: single node target now
node = frames.getnodes()[0]
info = frames.info[node]
npkgs = info['npkgs']

frames.setfps(fps)

nframes = frames.nframes

#
# connect each data set
#

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
l = plot_temp(ax, temp_plot_mean)

fig.tight_layout()

print 'generating %d frames' % nframes
st = time.time()
with writer.saving(fig, "m.mp4", 100):
    for i in range(nframes):
        d = temp_data[i]
        if not d == None:
            for p in range(npkgs):
                t = d['time']
                v = d['p%d' % p]['mean']
                temp_plot_mean[p].add(t,v)
            
        l.update(temp_plot_mean)

        writer.grab_frame()

elapsed = time.time() - st

print 'elapsed: %3lf' % elapsed
print '%.3f sec/frame' %  (float(elapsed)/nframes)
