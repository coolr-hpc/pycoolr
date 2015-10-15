#!/usr/bin/env python
#
# CPU related codes
#
# Contact: Kazutomo Yoshii <ky@anl.gov>
#

import os, sys, re, time

# local
from clr_misc import *

#
# Once instantiated, the following values are avaialble
#
# onlinecpus : a list holds all online cpus
# pkgcpus    : a dict holds per pkg cpus.  the key of the dict are pkgids
# nodecpus   : a dict holds per node cpus. the key of the dict are nodeids
#
# limitation: no support for runtime change
#
class cputopology:
    cpubasedir  = '/sys/devices/system/cpu/'
    nodebasedir = '/sys/devices/system/node/'

    def parserange(self,fn):
        tmp = readbuf( fn )
        ret = []
        for t in tmp.split(','):
            ab = re.findall('[0-9]+', t)
            if len(ab) == 2 :
                ret = ret + range( int(ab[0]), int(ab[1])+1 )
            elif len(ab) == 1:
                ret = ret + [int(ab[0])]
            else:
                print 'unlikely at cputoplogy.parserange():',ab
                sys.exit(1)
        return ret

    def parsemask(self,fn):
        tmp = readbuf( fn )
        tmp = tmp.rstrip()
        maskstrs = tmp.split(',')
        maskstrs.reverse()
        shift=0
        ret = []
        for mstr in maskstrs:
            bmint = long(mstr,16)
            for i in range(0,32):
                if (bmint&1) == 1:
                    ret.append(i+shift)
                bmint = bmint >> 1
            shift = shift + 32

        return ret

    def detect(self):
        self.onlinecpus = self.parserange(self.cpubasedir + 'online')

        self.pkgcpus = {}
        for cpuid in self.onlinecpus:

            pkgidfn = self.cpubasedir + "cpu%d/topology/physical_package_id" % (cpuid)
            pkgid = int(readbuf(pkgidfn))
            if not self.pkgcpus.has_key(pkgid) :
                self.pkgcpus[pkgid] = []
            self.pkgcpus[pkgid].append(cpuid)

        self.cpu2coreid = {}
        self.core2cpuid = {}
        for pkgid in self.pkgcpus.keys() :
            for cpuid in self.pkgcpus[pkgid]:
                coreidfn = self.cpubasedir + "cpu%d/topology/core_id" % (cpuid)
                coreid = int(readbuf(coreidfn))
                self.cpu2coreid[cpuid] = (pkgid, coreid)
                self.core2cpuid[(pkgid, coreid)] = cpuid

        self.onlinenodes = self.parserange(self.nodebasedir + 'online')
        self.nodecpus = {}
        for n in self.onlinenodes:
            self.nodecpus[n] = self.parsemask(self.nodebasedir + "node%d/cpumap" % (n))

    def __init__(self):
        self.detect()


class osconfig :

    def update(self):
        tmp = readbuf( '/proc/version' )
        self.version = tmp.split()[2]

        # assume that all cpu have the same setting for this experiment
        self.driver = ''
        d = '/sys/devices/system/cpu/cpu0/cpufreq'
        if os.path.exists(d):
            self.freqdriver = 'acpi_cpufreq'
            fn = d + "/scaling_driver"
            self.driver = readbuf( fn ).rstrip()
            fn = d + "/scaling_governor"
            self.governor = readbuf( fn ).rstrip()
            fn = d + "/scaling_cur_freq"
            self.cur_freq = readbuf( fn ).rstrip()

        d = "/sys/devices/system/cpu/intel_pstate"
        if os.path.exists(d):
            self.freqdriver = 'pstate'
            k = 'max_perf_pct'
            pmax = readbuf( "%s/%s" % (d,k) ).rstrip()
            k = 'min_perf_pct'
            pmin = readbuf( "%s/%s" % (d,k) ).rstrip()
            k = 'no_turbo'
            noturbo = readbuf( "%s/%s" % (d,k) ).rstrip()
            self.pstate = "%s/%s/%s" % (pmax,pmin,noturbo)

        d = "/sys/devices/system/cpu/turbofreq"
        if os.path.exists(d):
            self.freqdriver = 'coolrfreq'
            self.policy = d + '/pstate_policy'

    def __init__ (self):
        self.update()

#
# ad hoc implementation
def readfreq():
    ret = [0.0 for i in range(0,16)]
    for i in range(0,16):
        fn = '/var/tmp/amperf%d' % i
        ret[i] = 1.2 # minimum freq if failed to retry
        for retry in range(0,10):
            try :
                f = open(fn)
                ret[i] = float(f.readline())
                f.close()
            except:
                time.sleep(0.01)
                continue
            break

    return ret


def  testosconfig():
    print '=== ', sys._getframe().f_code.co_name

    oc = osconfig()
    print oc.version
    print oc.freqdriver
    print

def testcputopology():
    print '=== ', sys._getframe().f_code.co_name
    ct = cputopology()
    print
    print 'No. of online cpus: ', len(ct.onlinecpus)
    print
    for p in sorted(ct.pkgcpus.keys()):
        print 'pkg%d:' % p, len(ct.pkgcpus[p]), ct.pkgcpus[p]
        print '   cpuid:', 
        for cpuid in ct.pkgcpus[p]:
            print ct.cpu2coreid[cpuid],ct.cpu2coreid[cpuid][1],
        print
    print
    for n in sorted(ct.nodecpus.keys()):
        print 'node%d:' % n, len(ct.nodecpus[n]), ct.nodecpus[n] 

        print '   cpuid:', 
        for cpuid in ct.nodecpus[n]:
            print ct.cpu2coreid[cpuid],
        print
    print

def testfreq():
    print '=== ', sys._getframe().f_code.co_name

    freqs = readfreq()

    print freqs[0:8]
    print freqs[8:16]
    

if __name__ == '__main__':

    testosconfig()

    testcputopology()

    # testfreq()

