#!/usr/bin/env python
#
# reading the APERF and MPERF register via the amperf sysfs provided
# by the coolrfreq driver
#
# This code requires the coolrfreq driver
#
# Contact: Kazutomo Yoshii <ky@anl.gov>
#

import re, os, sys, time
import numpy as np
from clr_nodeinfo import *

class amperf_reader :

    def __init__ (self):
        self.ct = cputopology()

        self.init = False
        if os.path.exists('/sys/devices/system/cpu/cpu0/amperf'):
            self.init = True
        else:
            print 'Warning: the amperf sysfs is unavailable'

        self.samples = [ None, None ]
        self.sidx = 0

        self.sample()
        time.sleep(.1)
        self.sample()

    def read(self):
        if not self.init:
            return None
        ret = {}
        for p in sorted(self.ct.pkgcpus.keys()):
            perpkg = {}
            for cpuid in self.ct.pkgcpus[p]:
                fn = "/sys/devices/system/cpu/cpu%d/amperf" % cpuid
                with open(fn, 'r') as f:
                    t = f.readline().split()
                    vals = []
                    for v in t:
                        vals.append(int(v))

                    perpkg['c%d' % cpuid] = vals
            ret['p%d' % p] = perpkg
            ret['time'] = time.time()
        return ret

    def sample(self):
        self.samples[self.sidx] = self.read()

        if self.sidx == 0:
            self.sidx = 1
        else:
            self.sidx = 0

    def firstidx(self):
        return self.sidx

    def secondidx(self):
        if self.sidx == 0:
            return 1
        return 0

    def getdiff(self):
        d = {}
        f = self.samples[self.firstidx()]
        s = self.samples[self.secondidx()]
        
        for kp in f.keys():
            if kp == 'time':
                d['time'] = s[kp] - f[kp] 
            else:
                tmp = {}
                for kc in f[kp].keys():
                    vals = []
                    for i in range(0,2):
                        vals.append(s[kp][kc][i] - f[kp][kc][i])
                    tmp[kc] = vals
                d[kp] = tmp
        return d

    def getavgGHz(self, d):
        ret = {}
        dt = d['time']

        for kp in d.keys():
            if kp != 'time':
                tmp = {}
                for kc in d[kp].keys():
                    tmp[kc] = d[kp][kc][0] / dt * 1e-9
                ret[kp] = tmp

        return ret

    def getpkgstats(self, p):
        ret = {}

        for k in p.keys():
            tmp = []
            for c in p[k].keys():
                tmp.append(p[k][c])

            ret[k] = [np.mean(tmp), np.std(tmp), np.min(tmp), np.max(tmp)]

        return ret


if __name__ == '__main__':

    amp = amperf_reader()

    while True:
        amp.sample()
        d = amp.getdiff()
        f = amp.getavgGHz(d)
        for kp in f.keys():
            for kc in f[kp].keys():
                print '%.2lf' % f[kp][kc],
            print '    ',
        print ''

        time.sleep(1)

