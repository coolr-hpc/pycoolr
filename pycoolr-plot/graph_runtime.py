#!/usr/bin/env python

from listrotate import *

from clr_matplot_graphs import *

# the class name should match with the module name
class graph_runtime:
    def __init__(self, params, layout):
        # limited size list for time-series data
        self.runtime_lr = listrotate2D(length=params['lrlen'])
        self.es_lr = listrotate2D(length=params['lrlen'])

        # axis for graph
        self.ax = layout.getax()
        self.ax_es = layout.getax()
        # self.axbar = layout.getax()

    def update(self, params, sample):
        if sample['node'] == params['targetnode'] and sample['sample'] == 'argobots':
            #
            # data handling
            #
            t = sample['time'] - params['ts']

            ncpus = params['info']['ncpus']

            num_es = sample['num_es']
            tmpy = [ 0.0 for i in range(ncpus) ]
            for i in range(num_es):
                tmpy[i] += sample['num_threads']['es%d'%i]
                tmpy[i] += sample['num_tasks']['es%d'%i]

            self.runtime_lr.add(t, np.mean(tmpy), np.std(tmpy))
            self.es_lr.add(t, num_es)
            #
            # graph handling : line+errbar
            #
            pdata = self.runtime_lr
            gxsec = params['gxsec']

            ax = self.ax
            ax.cla()
            ax.set_xlim([t-gxsec, t])

            x = pdata.getlistx()
            y = pdata.getlisty()
            e = pdata.getlisto()
            ax.plot(x,y, scaley=True,  label='')
            ax.errorbar(x,y,yerr=e, lw=.2, label = '')

            ax.set_xlabel('Time [S]')
            ax.set_ylabel('# of Work Units')
            ax.set_title('Argobots: %s' % params['targetnode'])
            # self.ax.legend(loc='lower left', prop={'size':9})

            #
            # graph handling : simple line
            #
            pdata = self.es_lr
            ax = self.ax_es

            ax.cla()
            ax.set_xlim([t-gxsec, t])
            ax.set_ylim([0, ncpus+2])

            x = pdata.getlistx()
            y = pdata.getlisty()
            ax.step(x,y, scaley=True,  label='', color='#556677')

            ax.set_xlabel('Time [S]')
            ax.set_ylabel('# of Execution Streams')
            ax.set_title('Argobots: %s' % params['targetnode'])

            #
            # graph handling : bar
            #
            #offset = 0
            #ind = np.arange(ncpus) + offset
            #self.axbar.cla()
            #self.axbar.set_xlim([offset, offset+ncpus])
            #self.axbar.bar(ind, tmpy, width = .6, edgecolor='none', color='#bbbbcc' )
            #self.axbar.set_xlabel('Stream ID')
            #self.axbar.set_ylabel('# of Work Units')
            #self.axbar.set_title('Argobots: %s' % params['targetnode'])
