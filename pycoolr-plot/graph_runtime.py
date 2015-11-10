#!/usr/bin/env python

from listrotate import *

from clr_matplot_graphs import *

# the class name should match with the module name
class graph_runtime:
    def __init__(self, params, layout):
        self.runtime_lr = listrotate2D(length=params['lrlen'])
        self.ax = layout.getax()
        self.axbar = layout.getax()

    def update(self, params, sample):
        if sample['node'] == params['targetnode'] and sample['sample'] == 'argobots':
            #
            # data handling
            #
            t = sample['time'] - params['ts']

            num_es = sample['num_es']
            tmpy = [ 0.0 for i in range(num_es) ]
            for i in range(num_es):
                tmpy[i] += sample['num_threads']['es%d'%i]
                tmpy[i] += sample['num_tasks']['es%d'%i]

            self.runtime_lr.add(t,np.mean(tmpy),np.std(tmpy))
            #
            # graph handling : line+errbar
            #
            pdata = self.runtime_lr
            gxsec = params['gxsec']

            self.ax.cla()
            self.ax.set_xlim([t-gxsec, t])

            x = pdata.getlistx()
            y = pdata.getlisty()
            e = pdata.getlisto()
            self.ax.plot(x,y, scaley=True,  label='')
            self.ax.errorbar(x,y,yerr=e, lw=.2, label = '')

            self.ax.set_xlabel('Time [S]')
            self.ax.set_ylabel('ES ??') # fix this
            self.ax.set_title('Argobots: %s' % params['targetnode'])
            # self.ax.legend(loc='lower left', prop={'size':9})

            #
            # graph handling : bar
            #
            offset = 0
            ind = np.arange(num_es) + offset
            self.axbar.cla()
            self.axbar.bar(ind, tmpy, width = .6, edgecolor='none', color='#ddddee' )
            self.axbar.set_xlabel('Stream ID')
            self.axbar.set_ylabel('ES ??') # fix this
            self.axbar.set_title('Argobots: %s' % params['targetnode'])
