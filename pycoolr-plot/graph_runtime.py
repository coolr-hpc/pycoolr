#!/usr/bin/env python

from listrotate import *

from clr_matplot_graphs import *

# XXX: the class name should match with the module name
class graph_runtime:
    def __init__(self, params, idx):
        self.runtime_lr = listrotate2D(length=params['lrlen'])

        self.ax = plt.subplot(params['row'], params['col'], idx)
        self.pl = plot_runtime(self.ax, params, self.runtime_lr) # , titlestr="%s" % targetnode)

    def update(self, params, sample):
        if sample['node'] == params['targetnode'] and sample['sample'] == 'argobots':
            #
            # data handling
            #
            t = sample['time'] - params['ts']
            tmp = []
            for tmpk in sample['num_threads'].keys():
                tmp.append(int(sample['num_threads'][tmpk]))

            self.runtime_lr.add(t,np.mean(tmp),np.std(tmp))
            #
            # graph handling
            #
            pdata = self.runtime_lr
            gxsec = params['gxsec']

            self.ax.cla()
            self.ax.set_xlim([t-gxsec, t])

            x = pdata.getlistx()
            y = pdata.getlisty()
            e = pdata.getlisto()
            self.ax.plot(x,y, scaley=True,  label='')
            self.ax.errorbar(x,y,yerr=e, lw=.2,  label = '')

            self.ax.set_xlabel('Time [S]')
            self.ax.set_ylabel('Runtime')
            # self.ax.legend(loc='lower left', prop={'size':9})


