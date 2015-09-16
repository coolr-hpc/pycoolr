#!/usr/bin/env python
#
# coolr cpufreq related codes
#
# There is no perfect way to read the CPU clock on x86.  We need to
# read TSC, APERF and MPERF to estimate the current cpu clock on x86.
#
# This code requires the cpustat driver
#
# Contact: Kazutomo Yoshii <ky@anl.gov>
#

import os, sys, time
import struct
import copy
import clr_nodeinfo

#an example the content of cpustat
#id                    0
#aperf     4926926121023
#mperf     4582847073452
#perf_bias             8
#ucc     281462841145699
#urc                   0
#perf_target        8448
#perf_status        8448
#pstate               33
#turbo_disengage       0
#tsc    1117245755950154

class cpustatvals:
    def cpustatfn(self, cpuid):
        return "/sys/devices/system/cpu/cpu%d/cpustat/cpustat" % cpuid

    def __init__(self, cpuid):
        self.u64max = (1 << 64) - 1
        self.d = {}
        self.cpuid = cpuid

    def parse(self):
        self.d = {} # clear d's contents
        self.d['time'] = time.time()
        with open(self.cpustatfn(self.cpuid)) as f:
            while True:
                l = f.readline()
                if not l:
                    break
                a = l.split()
                if a[0] in ('id', 'aperf', 'mperf', 'pstate', 'tsc'):
                    self.d[a[0]] = int(a[1])

    def pr(self):
        for k in ('id', 'aperf', 'mperf', 'pstate', 'tsc'):
            print '%s=%d ' % (k, self.d[k]),
        print 
    
    def diff_u64(self, v1, v2): # v1 - v2
        if v1 >= v2:
            return v1 - v2
        return (self.u64max -v2) + v1

    def calc_cpufreq(self,prev): # prev is an object of cpustatvals
        if not (prev.d.has_key('tsc') and self.d.has_key('tsc')):
                    return 0.0
        tmp = {}
        for k in ('tsc', 'aperf', 'mperf'):
            tmp[k] = float(self.diff_u64(self.d[k], prev.d[k]))

        dt = self.d['time'] - prev.d['time']
        freq = tmp['aperf'] / tmp['mperf']
        freq *= tmp['tsc']
        freq *= 1e-9  # covert it to GHz
        freq /= dt

        return freq


class cpufreq_reader:

    def __init__(self):
        # I don't know how to create an object in a singleton manner in python
        # so simply instantiating an object of cputopology again here.
        topo = clr_nodeinfo.cputopology()
        topo.detect()

        self.cpus = topo.onlinecpus

        self.init = False

        for cpuid in self.cpus:
            tmp = cpustatvals(cpuid) # just for cpustatfn
            statpath = tmp.cpustatfn(cpuid)
            if not os.path.exists(statpath):
                print 'Not found', statpath
                return

        self.init = True
        self.cnt = 0
        self.samples = [
            [cpustatvals(i) for i in self.cpus],
            [cpustatvals(i) for i in self.cpus] ]

    def sample(self):
        idx = self.cnt % 2
        for cpuid in self.cpus:
            self.samples[idx][cpuid].parse()
        self.cnt = self.cnt + 1

    def cpufreqs(self):
        ret = [0.0 for i in self.cpus]
        if self.cnt < 2:
            return ret

        idxprev = 0
        idxcur = 1
        if (self.cnt % 2) == 1:
            idxprev = 1
            idxcur = 0

        for cpuid in self.cpus:
            ret[cpuid] = self.samples[idxcur][cpuid].calc_cpufreq(
                self.samples[idxprev][cpuid])

        return ret

if __name__ == '__main__':

    freq = cpufreq_reader()

    for i in range(0, 10):
        freq.sample()
        for f in freq.cpufreqs():
            print '%.1lf ' % f,
        print
        time.sleep(.5)
        
