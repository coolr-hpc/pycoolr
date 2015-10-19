#
# matplot graph class definition
#
# backend independent implementation
#
# Kazutomo Yoshii <ky@anl.gov>
#

import os, sys

import matplotlib.pyplot as plt
import matplotlib.animation as manimation
#import matplotlib.collections as collections
import matplotlib.cm as cm
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.cbook import get_sample_data
from matplotlib._png import read_png

from listrotate import *

class plot_line_err:
    def __init__(self, ax, params, pdata, ptype = 'temp' ):
        self.ax = ax

        # unfortunately, I couldn't figure out how to update errorbar correctly
        self.update(params, pdata, ptype)
        
        
    def update(self, params, pdata, ptype = 'temp'):
        cfg = params['cfg']

        cur_t = params['cur']
        gxsec = params['gxsec']

        self.ax.cla() # don't know how to update errorbar
        if ptype == 'temp':
            self.ax.axis([cur_t-gxsec, cur_t, cfg['mintemp'], cfg['maxtemp']]) # [xmin,xmax,ymin,ymax]
        elif ptype == 'freq':
            self.ax.axis([cur_t-gxsec, cur_t, cfg['freqmin'], cfg['freqmax']]) # [xmin,xmax,ymin,ymax]
        else:
            self.ax.axis([cur_t-gxsec, cur_t, 0, 100]) # [xmin,xmax,ymin,ymax]

        pkgid = 0
        for t in pdata:
            x = t.getlistx()
            y = t.getlisty()
            e = t.getlisto()
            self.ax.plot(x,y,scaley=False,label='PKG%d'%pkgid)
            self.ax.errorbar(x,y,yerr=e, lw=.2, color=params['pkgcolors'][pkgid], label = '')
            pkgid += 1

        # we need to update labels everytime because of cla()
        self.ax.set_xlabel('Uptime [S]')
        if ptype == 'temp':
            self.ax.set_ylabel('Core temperature [C]')
        elif ptype == 'freq':
            self.ax.set_ylabel('Frequency [GHz]')
        else:
            self.ax.set_ylabel('Unknown')

# below are kind of examples
#


class plotline:
    def __init__(self, ax, x, y):
        self.ax = ax
        self.line, = ax.plot(x,y)

        self.ax.axhspan( 0.7, 1.0, facecolor='#eeeeee', alpha=1.0)
        
    def update(self, x, y):
        self.line.set_data(x, y)


        
class plotcolormap:
    def __init__(self, ax, X):
        self.ax = ax
        self.im = self.ax.imshow(X, cmap=cm.jet, interpolation='nearest')
        self.im.set_cmap('spectral')
        self.im.set_clim(0, 1.5)
        
        f = plt.gcf()
        f.colorbar(self.im)

    def update(self,X):
        self.im.set_array(X)

class plotbar:
    def __init__(self, ax, x, y):
        self.ax = ax
        self.rects = ax.bar(x, y)

    def update(self, y):
        for r, h in zip(self.rects, y):
            r.set_height(h)

class ploterrorbar:
    def __init__(self, ax, x, y, e):
        self.ax = ax
        l, (b, t), v = ax.errorbar(x, y, e)
        self.line = l
        self.bottom = b
        self.top = t
        self.vert = v

    def update(self, x, y, e):
        # XXX: this is a bit brute-force
        # I couldn't figure out how to update vert
        self.ax.cla()
        self.ax.errorbar(x, y, e)

class plottext:
    def ypos(self,i):
        return 1.0 - 0.05*i

    def __init__(self, ax, n):
        self.ax = ax

        dir=os.path.abspath(os.path.dirname(sys.argv[0]))

        ax.axis([0,1,0,1])
        ax.axes.get_xaxis().set_visible(False)
        ax.axes.get_yaxis().set_visible(False)
        ax.set_frame_on=True

        ax.plot( [ 0.1, 0.2], [0.96, 0.96], color='blue',  linewidth=2 )
        ax.plot( [ 0.1, 0.2], [0.91, 0.91], color='green', linewidth=2 )
        ax.plot( [ 0.1, 0.2], [0.86, 0.86], color='red',   linewidth=1 )

        self.text1 = ax.text( 0.3, self.ypos(2), '%d' % n )

        fn = get_sample_data("%s/coolr-logo-poweredby-48.png" % dir, asfileobj=False)
        arr = read_png(fn)
        imagebox = OffsetImage(arr, zoom=0.4)
        ab = AnnotationBbox(imagebox, (0, 0),
                            xybox=(.75, .12),
                            xycoords='data',
                            boxcoords="axes fraction",
                            pad=0.5)
        ax.add_artist(ab)

    def update(self, n):
        self.text1.set_text('%d' % n)
