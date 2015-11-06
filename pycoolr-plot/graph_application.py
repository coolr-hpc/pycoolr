#!/usr/bin/env python

from listrotate import *

from clr_matplot_graphs import *


# the class name should match with the module name
class graph_application:
    def __init__(self, params, layout):
        self.sec_per_node_lr = listrotate2D(length=params['lrlen'])
        self.watt_per_node_lr = listrotate2D(length=params['lrlen'])
        self.sec_lr = listrotate2D(length=params['lrlen'])

        self.ax_sec_per_node = layout.getax()
        self.ax_watt_per_node = layout.getax()
        self.ax_sec = layout.getax()

    def update(self, params, sample):
        if sample['node'] == params['targetnode'] and sample['sample'] == 'application':
            #
            # data handling
            #
            t = sample['time'] - params['ts']

            self.sec_per_node_lr.add(t,sample['#TE_per_sec_per_node'])
            self.watt_per_node_lr.add(t,sample['#TE_per_watt_per_node'])
            self.sec_lr.add(t,sample['#TE_per_sec'])

            #
            # graph handling
            #
            gxsec = params['gxsec']
            #
            #

            ax = self.ax_sec_per_node
            pdata = self.sec_per_node_lr

            ax.cla()
            ax.set_xlim([t-gxsec, t])

            x = pdata.getlistx()
            y = pdata.getlisty()

            ax.plot(x,y, scaley=True,  label='')
            ax.set_xlabel('Time [S]')
            ax.set_ylabel('TE/sec/Node')
            #
            #
            ax = self.ax_watt_per_node
            pdata = self.watt_per_node_lr

            ax.cla()
            ax.set_xlim([t-gxsec, t])

            x = pdata.getlistx()
            y = pdata.getlisty()

            ax.plot(x,y, scaley=True,  label='')
            ax.set_xlabel('Time [S]')
            ax.set_ylabel('TE/Watt/Node')

            #
            #
            ax = self.ax_sec
            pdata = self.sec_lr

            ax.cla()
            ax.set_xlim([t-gxsec, t])

            x = pdata.getlistx()
            y = pdata.getlisty()

            ax.plot(x,y, scaley=True,  label='')
            ax.set_xlabel('Time [S]')
            ax.set_ylabel('TE/Sec')
