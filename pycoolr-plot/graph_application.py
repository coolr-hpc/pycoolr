#!/usr/bin/env python

from listrotate import *

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


# the class name should match with the module name
class graph_application:
    def __init__(self, params, layout):
        self.ngraphs = 0

        if not params['cfg'].has_key('appsamples'):
            return

        self.ngraphs = len(params['cfg']['appsamples'])
        print 'samples', params['cfg']['appsamples']


        self.data_lr = [listrotate2D(length=params['lrlen']) for i in range(self.ngraphs)]
        self.ax = [layout.getax() for i in range(self.ngraphs)]

    def update(self, params, sample):
        if self.ngraphs == 0:
            return

        if sample['node'] == params['targetnode'] and sample['sample'] == 'application':
            #
            # data handling
            #
            t = sample['time'] - params['ts']

            for i in range(self.ngraphs):
                self.data_lr[i].add(t,sample[params['cfg']['appsamples'][i]])

            #
            # graph handling
            #
            gxsec = params['gxsec']
            #
            #

            for i in range(self.ngraphs):
                ax = self.ax[i]
                pdata = self.data_lr[i]
                label = params['cfg']['appsamples'][i]
                ax.cla()
                ax.set_xlim([t-gxsec, t])

                x = pdata.getlistx()
                y = pdata.getlisty()

                ax.step(x,y, scaley=True, label='')
                ax.set_xlabel('Time [S]')
                ax.set_ylabel(label)

                ax.set_title('%s: %s' % (params['cfg']['appname'], params['targetnode']) )

        else:
            t = sample['time'] - params['ts']
            gxsec = params['gxsec']

            for i in range(self.ngraphs):
                self.ax[i].set_xlim([t-gxsec, t])
                self.ax[i].set_title('%s: %s' % (params['cfg']['appname'], params['targetnode']) )

