#!/usr/bin/env python

#
# coolr monitoring library
#
# the following kernel modules must be installed
#
# - coretemp
# - intel_powerclamp
#
# the following kernel modules are optional
#
# - acpi_power_meter
# - amperf
#
# written by Kazutomo Yoshii <ky@anl.gov>
#

import os, sys, re, time
import numpy as np
import subprocess
import threading
import signal

# local
import keypress
import clr_rapl
import clr_hwmon
import clr_cpuinfo

from clr_misc import *

#
#

import getopt

def usage():
    print ''
    print 'Usage: coolrmon.py [options] cmd args..'
    print ''
    print '[options]'
    print ''
    print '--runtests : run internal test funcs'
    print '-C or --cooldown temp : wait until the max coretemp gets below temp'
    print ''

class coolrmon_tracer:
    def sample_temp(self,label):
        temp = self.ctr.readtempall()

        # constructing a json output
        s  = '{"sample":"temp", "time":%.3f' % (time.time() - self.start_time0)
        s += ',"label"="%s"' % label
        for p in sorted(temp.keys()):
            s += ',"p%d":{' % p

            firstitem = True
            for c in sorted(temp[p].keys()):
                if firstitem:
                    s += '"%s":%d' % (c, temp[p][c])
                    firstitem = False
                else:
                    s += ',"%s":%d' % (c, temp[p][c])
            s += '}'
        s += '}'

        self.logger(s)

        return temp

    def start_energy_counter(self):
        if not self.rapl.initialized():
            return

        e = self.rapl.readenergy()
        self.start_time_e = time.time()

        self.totalenergy = {}
        self.lastpower = {}

        for k in sorted(e.keys()):
            if k != 'time':
                self.totalenergy[k] = 0.0
                self.lastpower[k] = 0.0
        self.prev_e = e

    def read_energy_acc(self):
        if not self.rapl.initialized():
            return

        e = self.rapl.readenergy()

        de = self.rapl.diffenergy(self.prev_e, e)

        for k in sorted(e.keys()):
            if k != 'time':
                self.totalenergy[k] += de[k]
                self.lastpower[k] = de[k]/de['time']/1000.0/1000.0;

        self.prev_e = e

        return e

    def stop_energy_counter(self):
        if not self.rapl.initialized():
            return

        e = self.read_energy_acc()
        self.stop_time = time.time()


    def sample_energy(self, label):
        if not self.rapl.initialized():
            return

        if label == 'run' :
            e = self.read_energy_acc()
        else:
            e = self.rapl.readenergy()

        # constructing a json output
        s  = '{"sample":"energy","time":%.3f' % (e['time'] - self.start_time0)
        s += ',"label"="%s"' % label
        for k in sorted(e.keys()):
            if k != 'time':
                s += ',"%s":%d' % ( self.rapl.shortenkey(k), e[k])
        s += '}'
        self.logger(s)

        return e

    def cooldown(self,label):
        if self.cooldowntemp < 0:
            return

        while True: 
            temp = self.sample_temp(label)
            e = self.sample_energy(label)

            # currently use only maxcoretemp
            maxcoretemp = self.ctr.getmaxcoretemp(temp)
            if maxcoretemp < self.cooldowntemp:
                break
            time.sleep(self.intervalsec)

    def setcooldowntemp(self,v):
        self.cooldowntemp = v

    def setinterval(self,isec):
        self.intervalsec = isec 

    def setlogger(self,func):
        self.logger = func

    def defaultlogger(self,str):
        print str

    def __init__ (self):
        # default values
        self.cooldowntemp = 40  # depend on arch
        #self.output = sys.stdout
        self.intervalsec = 1
        self.logger = self.defaultlogger
        # instantiate class
        self.ctr = clr_hwmon.coretemp_reader()
        self.rapl = clr_rapl.rapl_reader()
        self.oc = clr_cpuinfo.osconfig()
        self.ct = clr_cpuinfo.cputopology()

    def showconfig(self):
        s  = '{"kernelversion":"%s"' % self.oc.version
        s += ',"cpufreq_driver":"%s"' % self.oc.driver
        s += ',"cpufreq_governor":"%s"' % self.oc.governor
        s += ',"cpufreq_cur_freq":%s' % self.oc.cur_freq

        npkgs = len(self.ct.pkgcpus.keys())
        s += ',"npkgs":%d' % npkgs

        if self.rapl.initialized():
            s += ',"max_energy_uj":{'
            firstitem = True
            for p in sorted(self.ct.pkgcpus.keys()):
                k = 'package-%d' % p  # does 'topology' and rapldriver follow the same numbering scheme?
                if firstitem :
                    firstitem = False
                else:
                    s += ','
                    s += '"p%d":%d' % (p, self.rapl.max_energy_range_uj_d[k])
                s += '}'

        self.logger(s)


    def tee(self,argv):
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE )

        while True:
            l = proc.stdout.readline()
            if not l:
                break
            print 'stdout:', l,

    def report_total_energy(self):
        if not self.rapl.initialized():
            return

        dt = self.stop_time - self.start_time_e
        # constructing a json output
        e = self.totalenergy
        s  = '{"total":"energy","difftime":%f' % (dt)
        for k in sorted(e.keys()):
            if k != 'time':
                s += ',"%s":%d' % (self.rapl.shortenkey(k), e[k])
        s += '}'
        self.logger(s)

    def sigh(signal, frame):
        self.kp.disable()
        sys.exit(1)

    def run(self, argv):
        self.showconfig()

        self.start_time0 = time.time()
        s = '{"starttime":%.3f}' % self.start_time0
        self.logger(s)

        if len(argv) == 0:
            signal.signal(signal.SIGINT, self.sigh)
            signal.signal(signal.SIGTERM, self.sigh)

            self.kp = keypress.keypress()
            self.kp.enable()
            self.start_energy_counter()
            while True:
                self.sample_temp('run')
                self.sample_energy('run')

                # constructing a json output
                if self.rapl.initialized():
                    totalpower = 0.0
                    s  = '{"sample":"power","time":%.3f' % (self.prev_e['time'] - self.start_time0)
                    for k in sorted(self.lastpower.keys()):
                        if k != 'time':
                            s += ',"%s":%.1f' % (self.rapl.shortenkey(k), self.lastpower[k])
                        # this is a bit ad hoc way to calculate the total. needs to be fixed later
                        if k.find("core") == -1:
                            totalpower += self.lastpower[k]
                    s += ',"total":%.1f' % (totalpower)
                    s += '}'
                    self.logger(s)

                time.sleep(self.intervalsec)
                if self.kp.available():
                    if self.kp.readkey() == 'q':
                        break
            self.stop_energy_counter()
            self.kp.disable()
            self.report_total_energy()
            return

        self.cooldown('cooldown')

        # spawn a process and start the sampling thread
        t = threading.Thread(target=self.tee, args=[argv])
        t.start()

        self.start_energy_counter()

        while True:
            if not t.isAlive():
                break

            self.sample_temp('run')
            self.sample_energy('run')

            time.sleep(self.intervalsec)

        self.stop_energy_counter()
        self.report_total_energy()
        self.cooldown('cooldown')

class log2file:
    def __init__(self, fn):
        try:
            self.f = open(fn, 'w')
        except:
            print 'Error: failed to open', fn
            self.f = sys.stdout

    def logger(self,str):
        self.f.write(str)

if __name__ == '__main__':

    shortopt = "hC:i:o:"
    longopt = ['runtests', 'cooldown=', 'interval=', 'output=']
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                                   shortopt, longopt)

    except getopt.GetoptError, err:
        print err
        usage()
        sys.exit(1)

    tr = coolrmon_tracer()

    for o, a in opts:
        if o in ('-h'):
            usage()
            sys.exit(0)
        elif o in ("--runtests"):
            testosconfig()
            testcputopology()
            testtemp()
            testrapl()
            sys.exit(0)
        elif o in ("-C", "--cooldown"):
            tr.setcooldowntemp(int(a))
        elif o in ("-i", "--interval"):
            tr.setinterval(float(a))
        elif o in ("-o", "--output"):
            l = log2file(a)
            tr.setlogger(l.logger)
        else:
            print 'Unknown:', o, a
    #
    #

    tr.run(args)

    sys.exit(0)
