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

def readbuf(fn):
    for retry in range(0,10):
        try:
            f = open( fn )
            l = f.readline()
            f.close()
            return l
        except:
            time.sleep(0.01)
            continue
    return ''

def readuptime():
    f = open( '/proc/uptime' ) 
    l = f.readline()
    v = l.split()
    return float( v[0] )

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
    def getpstate(self):
        d="/sys/devices/system/cpu/intel_pstate"
        if os.access(d, os.R_OK) :
            k = 'max_perf_pct'
            pmax = readbuf( "%s/%s" % (d,k) ).rstrip()
            k = 'min_perf_pct'
            pmin = readbuf( "%s/%s" % (d,k) ).rstrip()
            k = 'no_turbo'
            noturbo = readbuf( "%s/%s" % (d,k) ).rstrip()
            self.pstate = "%s/%s/%s" % (pmax,pmin,noturbo)

    def update(self):
        tmp = readbuf( '/proc/version' )
        self.version = tmp.split()[2]

        # assume that all cpu have the same setting for this experiment
        fn = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver"
        self.driver = readbuf( fn ).rstrip()
        fn = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        self.governor = readbuf( fn ).rstrip()
        fn = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
        self.cur_freq = readbuf( fn ).rstrip()

        self.getpstate()

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


class coretemp_reader :
    def parse_pkgtemp(self,fn):
        retval = -1
        try:
            f = open(fn , "r")
        except:
            return retval
        l = f.readline()
        m = re.search('Physical id ([0-9]+)', l )
        if m:
            retval=int(m.group(1))
        f.close()
        return retval

    def parse_coretemp(self,fn):
        retval = -1
        try:
            f = open(fn , "r")
        except:
            return retval
        l = f.readline()
        m = re.search('Core ([0-9]+)', l )
        if m:
            retval=int(m.group(1))
        f.close()
        return retval

    hwmondir = '/sys/class/hwmon/'

    class coretempinfo:
        def __init__(self):
            self.dir = ''
            self.coretempfns = {} # use coreid as key
            self.pkgtempfn = ''

    def __init__ (self):
        ct = cputopology()

        self.coretemp = {} # use pkgid as  key
        for d1 in os.listdir(self.hwmondir):
            # try to check see if 'name' contains 'coretemp'
            tmpdir = "%s%s" % (self.hwmondir,d1)
            drivername = readbuf("%s/name" % tmpdir).rstrip()
            if not drivername == "coretemp":
                continue

            pkgid = -1
            coretempfns = {}
            pkgtempfn = ''
            # parse all temp*_label files
            for d2 in os.listdir( tmpdir ):
                m = re.search( 'temp([0-9]+)_label', d2 )
                if m:
                    tempid=int(m.group(1))
                    coreid = self.parse_coretemp("%s/%s" % (tmpdir, d2))
                    if coreid >= 0 :
                        coretempfns[coreid] = "%s/temp%d_input" % (tmpdir, tempid)
                    else: # possibly pkgid
                        pkgtempfn = "%s/temp%d_input" % (tmpdir, tempid)
                        pkgid = self.parse_pkgtemp("%s/%s" % (tmpdir, d2))
                        if pkgid < 0 :
                            print 'unlikely: ', pkgtempfn



            cti = self.coretempinfo()
            cti.dir = tmpdir
            cti.coretempfns = coretempfns
            cti.pkgtempfn = pkgtempfn

            if pkgid < 0: # assume a single socket machine
                self.coretemp[0] = cti
            else:
                self.coretemp[pkgid] = cti

    def readtempall(self):
        ctemp = self.coretemp
        ret = {}
        for pkgid in sorted(ctemp.keys()):
            temps = {}
            if os.access(ctemp[pkgid].pkgtempfn, os.R_OK):
                val = int(readbuf(ctemp[pkgid].pkgtempfn))/1000
                temps['pkg'] = val
            for c in sorted(ctemp[pkgid].coretempfns.keys()):
                if os.access(ctemp[pkgid].coretempfns[c], os.R_OK):
                    val = int(readbuf(ctemp[pkgid].coretempfns[c]))/1000
                    temps[c] = val
            ret[pkgid] = temps
        return ret

    def getmaxcoretemp(self, temps):
        vals = []
        for pkgid in temps.keys():
            for c in temps[pkgid].keys():
                vals.append(temps[pkgid][c])
        return np.max(vals)
                    
    def readpkgtemp(self):
        fn = "%s_input" % self.pkgtempfns[pkgid].pkgfn
        f = open(fn) 
        v = int(f.readline())/1000.0
        f.close()
        return v

    def readcoretemp(self,pkgid):
        t = []
        for fnbase in self.pkgtempfns[pkgid].corefns:
            fn = "%s_input" % fnbase
            if not os.access( fn, os.R_OK ):
                continue  # cpu may become offline
            f = open(fn) 
            v = int(f.readline())/1000.0
            f.close()
            t.append(v)
        return t


class rapl_reader:
    dryrun = False
    rapldir='/sys/devices/virtual/powercap/intel-rapl'
    # 
    # e.g.,
    # intel-rapl:0/name
    # intel-rapl:0/intel-rapl:0:0/name
    # intel-rapl:0/intel-rapl:0:1/name
    def __init__ (self):
        self.dirs = {}
        self.max_energy_range_uj_d = {}

        if self.dryrun :
            return 

        for d1 in os.listdir(self.rapldir):
            dn = "%s/%s" % (self.rapldir,d1)
            fn = dn + "/name"
            if os.access( fn , os.R_OK ) :
                f = open( fn)
                l = f.readline().strip()
                f.close()
                if re.search('package-[0-9]+', l):
                    self.dirs[l] = dn
                    pkg=l
                    for d2 in os.listdir("%s/%s" % (self.rapldir,d1) ):
                        dn = "%s/%s/%s" % (self.rapldir,d1,d2)
                        fn = dn + "/name"
                        if os.access( fn, os.R_OK ) :
                            f = open(fn)
                            l = f.readline().strip()
                            f.close
                            if re.search('core|dram', l):
                                self.dirs['%s/%s' % (pkg,l)] = dn


        for k in sorted(self.dirs.keys()):
            fn = self.dirs[k] + "/max_energy_range_uj"
            try:
                f = open( fn )
            except:
                print 'Unable to open', fn
                sys.exit(0)
            self.max_energy_range_uj_d[k] = int(f.readline())
            f.close()

    def shortenkey(self,str):
        return str.replace('package-','p')

#        for k in sorted(self.dirs.keys()):
#            print k, self.max_energy_range_uj_d[k]


    def readenergy(self):
        ret = {}
        ret['time'] = time.time()
        if self.dryrun:
            ret['package-0'] = readuptime()*1000.0*1000.0
            return ret
        for k in sorted(self.dirs.keys()):
            fn = self.dirs[k] + "/energy_uj"
            v = -1
            for retry in range(0,10):
                try:
                    f = open( fn )
                    v = int(f.readline())
                    f.close()
                except:
                    continue
            ret[k] = v
        return ret

    def readpowerlimit(self):
        ret = {}
        if self.dryrun:
            ret['package-0'] = 100.0
            return ret
        for k in sorted(self.dirs.keys()):
            fn = self.dirs[k] + '/constraint_0_power_limit_uw'
            v = -1
            for retry in range(0,10):
                try:
                    f = open( fn )
                    v = int(f.readline())
                    f.close()
                except:
                    continue
            ret[k] = v / (1000.0 * 1000.0) # uw to w
        return ret

    def diffenergy(self,e1,e2): # e1 is prev and e2 is not
        ret = {}
        ret['time'] = e2['time'] - e1['time']
        for k in self.max_energy_range_uj_d:
            if e2[k]>=e1[k]:
                ret[k] = e2[k] - e1[k]
            else:
                ret[k] = (self.max_energy_range_uj_d[k]-e1[k]) + e2[k]
        return ret

    # calculate the average power from two energy values
    # e1 and e2 are the value returned from readenergy()
    # e1 should be sampled before e2
    def calcpower(self,e1,e2): 
        ret = {}
        delta = e2['time'] - e1['time']  # assume 'time' never wrap around
        ret['delta']  = delta
        if self.dryrun:
            k = 'package-0'
            ret[k] = e2[k] - e1[k]
            ret[k] /= (1000.0*1000.0) # conv. [uW] to [W]
            return ret

        for k in self.max_energy_range_uj_d:
            if e2[k]>=e1[k]:
                ret[k] = e2[k] - e1[k]
            else:
                ret[k] = (self.max_energy_range_uj_d[k]-e1[k]) + e2[k]
            ret[k] /= delta
            ret[k] /= (1000.0*1000.0) # conv. [uW] to [W]
        return ret

class hwmonpwr :
    def read(self):
        retval=-1
        fn = '/sys/class/hwmon/hwmon1/device/power1_average'
        try:
            f = open(fn , "r")
        except:
            return retval

        l = f.readline()
        retval = int(l) / 1000.0 / 1000.0  # uW to W
        f.close()
        return retval



#
#  test functions
#

def  testosconfig():
    print '=== ', sys._getframe().f_code.co_name

    oc = osconfig()
    print oc.version

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
            print ct.cpu2coreid[cpuid],
        print
    print
    for n in sorted(ct.nodecpus.keys()):
        print 'node%d:' % n, len(ct.nodecpus[n]), ct.nodecpus[n] 

        print '   cpuid:', 
        for cpuid in ct.nodecpus[n]:
            print ct.cpu2coreid[cpuid],
        print
    print

def testtemp():
    print '=== ', sys._getframe().f_code.co_name
    ctr = coretemp_reader()

    temp = ctr.readtempall()

    for p in sorted(temp.keys()):
        print 'pkg%d:' % p,
        for c in sorted(temp[p].keys()):
            print "%s=%d " % (c, temp[p][c]),
        print

    # measure the time to read all temp
    # note: reading temp on other core triggers an IPI, 
    # so reading temp frequency will icreate the CPU load
    print 'Measuring readtime() and getmaxcoretemp ...'
    for i in range(0,3):
        a = time.time()
        temp = ctr.readtempall()
        maxcoretemp = ctr.getmaxcoretemp(temp)
        b = time.time()
        print '  %.1f msec, maxcoretemp=%d' % ((b-a)*1000.0, maxcoretemp)
        time.sleep(1)

    print

def testrapl():
    print '=== ', sys._getframe().f_code.co_name

    rr = rapl_reader()

#    print rr.dirs

    for i in range(0,3):
        print '#%d reading rapl' % i
        e1 = rr.readenergy()
        time.sleep(1)
        e2 = rr.readenergy()
        p = rr.calcpower(e1,e2)
        for k in sorted(p):
            print k, p[k]

    print

def testfreq():
    print '=== ', sys._getframe().f_code.co_name

    freqs = readfreq()

    print freqs[0:8]
    print freqs[8:16]
    


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

        self.logger(s + '\n')

        return temp

    def start_energy_counter(self):
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
        e = self.rapl.readenergy()

        de = self.rapl.diffenergy(self.prev_e, e)

        for k in sorted(e.keys()):
            if k != 'time':
                self.totalenergy[k] += de[k]
                self.lastpower[k] = de[k]/de['time']/1000.0/1000.0;

        self.prev_e = e

        return e

    def stop_energy_counter(self):
        e = self.read_energy_acc()
        self.stop_time = time.time()


    def sample_energy(self, label):
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
        self.logger(s + '\n')

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
        self.ctr = coretemp_reader()
        self.rapl = rapl_reader()
        self.oc = osconfig()
        self.ct = cputopology()

    def showconfig(self):
        s  = '{"kernelversion":"%s"' % self.oc.version
        s += ',"cpufreq_driver":"%s"' % self.oc.driver
        s += ',"cpufreq_governor":"%s"' % self.oc.governor
        s += ',"cpufreq_cur_freq":%s' % self.oc.cur_freq

        npkgs = len(self.ct.pkgcpus.keys())
        s += ',"npkgs":%d' % npkgs
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

        self.logger(s + '\n')


    def tee(self,argv):
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE )

        while True:
            l = proc.stdout.readline()
            if not l:
                break
            print 'stdout:', l,

    def report_total_energy(self):
        dt = self.stop_time - self.start_time_e
        # constructing a json output
        e = self.totalenergy
        s  = '{"total":"energy","difftime":%f' % (dt)
        for k in sorted(e.keys()):
            if k != 'time':
                s += ',"%s":%d' % ( self.rapl.shortenkey(k), e[k])
        s += '}'
        self.logger(s + '\n')

    def sigh(signal, frame):
        self.kp.disable()
        sys.exit(1)

    def run(self, argv):
        self.showconfig()

        self.start_time0 = time.time()
        s = '{"starttime":%.3f}' % self.start_time0

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
                self.logger(s + '\n')

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
