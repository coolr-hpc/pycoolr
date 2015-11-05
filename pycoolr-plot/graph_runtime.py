#!/usr/bin/env python

from listrotate import *

from clr_matplot_graphs import *

# XXX: the class name should match with the module name
class graph_runtime:
    def __init__(self, params, idx):
        self.runtime_lr = listrotate2D(length=params['lrlen'])

        ax = plt.subplot(params['row'], params['col'], idx)
        self.pl = plot_runtime(ax, params, self.runtime_lr) # , titlestr="%s" % targetnode)

    def update(self, params, e):
        if e['node'] == params['targetnode'] and e['sample'] == 'argobots':
            t = e['time'] - params['ts']
            params['cur'] = t # this is used in update()
            tmp = []

            for tmpk in e['num_threads'].keys():
                tmp.append(int(e['num_threads'][tmpk]))

            self.runtime_lr.add(t,np.mean(tmp),np.std(tmp))
            pl_runtime.update(params, runtime_lr)



