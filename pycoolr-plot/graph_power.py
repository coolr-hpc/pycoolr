#!/usr/bin/env python

from listrotate import *

from clr_matplot_graphs import *

# the class name should match with the module name
class graph_power:
    def __init__(self, params, layout):
        self.npkgs = params['info']['npkgs']
        self.data_lr = {}
        self.data_lr['pkg'] = [listrotate2D(length=params['lrlen']) for i in range(self.npkgs)]
        self.data_lr['dram'] = [listrotate2D(length=params['lrlen']) for i in range(self.npkgs)]

        self.ax = layout.getax()
        self.pl = plot_rapl(self.ax, params, self.data_lr['pkg'], self.data_lr['dram'],\
                            titlestr='Node: %s' % params['targetnode'])
        
    def update(self, params, sample):
        if sample['node'] == params['targetnode'] and sample['sample'] == 'energy':

            t = sample['time'] - params['ts']
            params['cur'] = t # this is used in update()

            for pkgid in range(self.npkgs):
                tmppow = sample['power']['p%d'%pkgid]
                tmplim = sample['powercap']['p%d'%pkgid]
                tmppowdram =  sample['power']['p%d/dram'%pkgid]
                self.data_lr['pkg'][pkgid].add(t, tmppow, tmplim)
                self.data_lr['dram'][pkgid].add(t, tmppowdram)
            self.pl.update(params, self.data_lr['pkg'], self.data_lr['dram'])
