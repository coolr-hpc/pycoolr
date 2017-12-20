#!/usr/bin/env python

"""
COOLR RAPL package

The intel_rapl kernel module is required.

Contact: Kazutomo Yoshii <ky@anl.gov>
"""

import os, sys, re, time, getopt

import clr_nodeinfo

class rapl_reader:
    """The 'rapl_reader' class provides monitoring and controlling
    capabilities for Intel RAPL.

    This implentation parses sysfs entries created the intel_rapl
    kernel module.

    """
    re_domain  = re.compile('package-(\d+)$')
    re_domain_long  = re.compile('package-(\d+)(/\S+)?')
    re_domain_short = re.compile('p(\d+)(/\D+)?')

    def readint(self, fn):
        """A convenient function that reads the firs line in fn and returns
        an integer value
        """
        v = -1
        for retry in range(0,10):
            try:
                f = open( fn )
                v = int(f.readline())
                f.close()
            except:
                continue
        return v

    def writeint(self, fn, v):
        """A convenient function that writes an integer value to fn
        """

        ret = False
        try:
            f = open(fn, 'w')
            f.write('%d' % v)
            f.close()
            ret = True
        except:
            ret = False
        return ret


    def is_enabled(self):
        """Check see if RAPL is enabled

        The overhead of this call is around 80 usec, which is
        acceptable for reading energy since RAPL updates the internal
        energy counter in milliseconds (e.g., 10 msec).

        """
        return self.readint(self.rapldir + "/enabled")

    def write_enabled(self, val):
        """Write val to enabled

        For cases, even though sysfs reports enabled, we need to re-enable for power capping.
        """

    def __init__ (self):
        """Initialize the rapl_reader module

        It detects the power domains/subdomains by scanning the
        intel_rapl sysfs recurcively and creates a dict 'dirs' that
        contains sub-directory for available domains.  The existance
        of each domain is decided by the existance of a file name
        'name' (see below). It also creates a dict named
        'max_energy_range_uj_d' for the maximum energy range for the
        RAPL energy counter, which is used to calculate the counter
        wrapping.

        e.g.,
        intel-rapl:0/name
        intel-rapl:0/intel-rapl:0:0/name
        intel-rapl:0/intel-rapl:0:1/name
        """
        self.dryrun = False
        self.rapldir='/sys/devices/virtual/powercap/intel-rapl'

        self.dirs = {}
        self.max_energy_range_uj_d = {}
        self.ct = clr_nodeinfo.cputopology()

        if self.dryrun :
            return

        self.init = False
        if not os.path.exists(self.rapldir):
            return
        self.init = True

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

        self.start_energy_counter()

    def initialized(self):
        """Return whether or not it is initialized"""
        return self.init

    def shortenkey(self,str):
        """Convert a long name to a short name"""
        return str.replace('package-','p')

    def readenergy(self):
        """Read the energy consumption on all available domains

        Returns:
            A dict for energy consumptions on all available domains
        """
        if not self.initialized():
            return

        ret = {}
        ret['time'] = time.time()
        if self.dryrun:
            ret['package-0'] = readuptime()*1000.0*1000.0
            return ret
        for k in sorted(self.dirs.keys()):
            fn = self.dirs[k] + "/energy_uj"
            ret[k] = self.readint(fn)
        return ret


    def readpowerlimitall(self):
        """Read the current power limit values on all available domains

        Read all possible power caps, except package 'short_term', which
        will be supported later. This function is designed to be called
        from a slow path. return a dict with long domain names as keys
        and a value contains a dict with 'curW', 'maxW', 'enabled'

        Returns:
            A dict for power limit (power capping) values on all available domains
        """
        if not self.initialized():
            return

        ret = {}
        if self.dryrun:
            ret['package-0'] = 100.0
            return ret
        for k in sorted(self.dirs.keys()):
            dvals = {}
            v = self.readint( self.dirs[k] + '/constraint_0_power_limit_uw' )
            dvals['curW'] = v * 1e-6  # uw to w

            v = self.readint( self.dirs[k] + '/constraint_0_max_power_uw' )
            dvals['maxW'] = v * 1e-6  # uw to w

            dvals['enabled'] = False
            v = self.readint( self.dirs[k] + '/enabled' )
            if v == 1:
                dvals['enabled'] = True
            ret[k] = dvals
        return ret

    def diffenergy(self, e1, e2): # e1 is prev and e2 is now
        """Calculate the delta value between e1 and e2, considering the counter wrapping

        Args:
          e1: the previous energy value
          e2: the current energy value

        Returns:
          A dict for the energy delta values on all available domains and the time delta values
        """

        ret = {}
        ret['time'] = e2['time'] - e1['time']
        for k in self.max_energy_range_uj_d:
            if e2[k]>=e1[k]:
                ret[k] = e2[k] - e1[k]
            else:
                ret[k] = (self.max_energy_range_uj_d[k]-e1[k]) + e2[k]
        return ret

    def calcpower(self, e1, e2):
        """Calculate the average power from two energy values

        e1 and e2 are the value returned from readenergy()

        Args:
          e1: the previous energy value
          e2: the current energy value

        Returns:
          A dict for the average power consumption values on all available domains and the time delta values
        """
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


    def start_energy_counter(self):
        """Start or reset the energy counter
        """
        if not self.initialized():
            return

        self.start_time_e = time.time()
        self.totalenergy = {}
        self.lastpower = {}

        e = self.readenergy()
        for k in sorted(e.keys()):
            if k != 'time':
                self.totalenergy[k] = 0.0
                self.lastpower[k] = 0.0
        self.prev_e = e


    def read_energy_acc(self):
        """Read the accumulated energy consumption
        """
        if not self.initialized():
            return

        e = self.readenergy()

        de = self.diffenergy(self.prev_e, e)

        for k in sorted(e.keys()):
            if k != 'time':
                self.totalenergy[k] += de[k]
                self.lastpower[k] = de[k]/de['time']/1000.0/1000.0;
        self.prev_e = e

        return e

    def stop_energy_counter(self):
        """Stop the energy counter
        """

        if not self.initialized():
            return

        e = self.read_energy_acc()
        self.stop_time = time.time()

    def sample(self, accflag=False):
        """Sample the current counter values and return a dict
        """

        if not self.initialized():
            return

        e = self.readenergy()

        de = self.diffenergy(self.prev_e, e)

        for k in sorted(e.keys()):
            if k != 'time':
                if accflag:
                    self.totalenergy[k] += de[k]
                self.lastpower[k] = de[k]/de['time']/1000.0/1000.0
        self.prev_e = e

        ret = dict()
        ret['energy'] = dict()
        for k in sorted(e.keys()):
            if k != 'time':
                ret['energy'][self.shortenkey(k)] = e[k]

        ret['power'] = dict()
        totalpower = 0.0
        for k in sorted(self.lastpower.keys()):
            if k != 'time':
                ret['power'][self.shortenkey(k)] = self.lastpower[k]
                # this is a bit ad hoc way to calculate the total.
                # needs to be fixed later
                if k.find("core") == -1:
                    totalpower += self.lastpower[k]
        ret['power']['total'] = totalpower

        ret['powercap'] = dict()
        rlimit = self.readpowerlimitall()
        for k in sorted(rlimit.keys()):
            ret['powercap'][self.shortenkey(k)] = rlimit[k]['curW']

        return ret

    def sample_and_json(self, label = "", accflag = False, node = ""):
        """Sample the current counter values and creates a json string
        """

        if not self.initialized():
            return

        e = self.readenergy()

        de = self.diffenergy(self.prev_e, e)

        for k in sorted(e.keys()):
            if k != 'time':
                if accflag:
                    self.totalenergy[k] += de[k]
                self.lastpower[k] = de[k]/de['time']/1000.0/1000.0;
        self.prev_e = e

        # constructing a json output
        s  = '{"sample":"energy","time":%.3f' % (e['time'])
        if len(node) > 0:
            s += ',"node":"%s"' % node
        if len(label) > 0:
            s += ',"label":"%s"' % label
        s += ',"energy":{'
        firstitem = True
        for k in sorted(e.keys()):
            if k != 'time':
                if firstitem:
                    firstitem = False
                else:
                    s+=','
                s += '"%s":%d' % (self.shortenkey(k), e[k])
        s += '},'
        s += '"power":{'

        totalpower = 0.0
        firstitem = True
        for k in sorted(self.lastpower.keys()):
            if k != 'time':
                if firstitem:
                    firstitem = False
                else:
                    s+=','
                s += '"%s":%.1f' % (self.shortenkey(k), self.lastpower[k])
                # this is a bit ad hoc way to calculate the total. needs to be fixed later
                if k.find("core") == -1:
                    totalpower += self.lastpower[k]
        s += ',"total":%.1f' % (totalpower)
        s += '},'

        s += '"powercap":{'
        rlimit = self.readpowerlimitall()
        firstitem = True
        for k in sorted(rlimit.keys()):
            if firstitem:
                firstitem = False
            else:
                s+=','
            s += '"%s":%.1f' % (self.shortenkey(k), rlimit[k]['curW'])
        s += '}'

        s += '}'
        return s

    def total_energy_json(self):
        """Create a json string for the total energy consumption
        """
        if not self.initialized():
            return ''

        dt = self.stop_time - self.start_time_e
        # constructing a json output
        e = self.totalenergy
        s  = '{"total":"energy","difftime":%f' % (dt)
        for k in sorted(e.keys()):
            if k != 'time':
                s += ',"%s":%d' % (self.shortenkey(k), e[k])
        s += '}'
        return s


    def to_shortdn(self, n):
        """Convert to a short domain name form

        No conversion takes place if n is already a short form
        """

        m = self.re_domain_long.match(n)
        sn = ''
        if not m:
            return n
        else:
            sn = 'p%d' % int(m.group(1))
            if m.group(2):
                sn += '/'
                sn += m.group(2)[1:]
        return sn

    def to_longdn(self, n):
        """Convert to a long domain name form

        No conversion takes place if n is already a long form
        """

        m = self.re_domain_short.match(n)
        ln = ''
        if not m:
            return n
        else:
            ln = 'package-%d' % int(m.group(1))
            if m.group(2):
                ln += m.group(2)
        return ln

    def create_powerdomains_cpuids(self):
        """Create a mapping that represents the relationship between power domains and cpuids

        Return:
           A dict with power domain (interger) as key and a list of cpuids as content
        """
        ret = {}
        for pd in self.readpowerlimitall().keys():
            m = self.re_domain.match(pd)
            if m:
                pkgid = int(m.group(1))
                ret[pkgid] = self.ct.pkgcpus[pkgid]
        return ret

    def get_powerdomains(self):
        """Return a list of available power domains

        Return:
           A list that contains all possible power domain names (long-name string)
        """
        return self.readpowerlimitall().keys

    def get_powerlimits(self):
        """Return a dict of the current power limit values on all available power domains

        Return:
           A dict with long-name power domain string as key and a dict that includes capping information as content
        """
        return self.readpowerlimitall()

    def _set_powerlimit(self, rrdir, newval, id = 0):
        """Internal method to set new power limit value
        """

        fn = rrdir + '/constraint_%d_power_limit_uw' % id
        uw = newval * 1e6
        try:
            f = open(fn, 'w')
        except:
            print 'Failed to update:', fn, '(root privilege is required)'
            return
        f.write('%d' % uw)
        f.close()

    def set_powerlimit(self, newval, dom):
        """Set new power limit value to specified power domain "dom"

        Args:
           newval: new power limit value in Watt
           dom: target power domain. both long or short name forms are accepted
        """
        dom_ln = to_longdn(dom)
        l = self.dirs[dom_ln]
        self._set_powerlimit(l, newval)

    def set_powerlimit_pkg(self, newval):
        """Set new power limit value to all possible top-level CPU packages
        """

        rlims = self.readpowerlimitall()
        for k in rlims.keys():
            if re.findall('package-[0-9]$', k):
                self._set_powerlimit(self.dirs[k], newval)

def usage():
    print 'clr_rapl.py [options]'
    print ''
    print '--show [pkgid]:   show the current setting'
    print '--limitp val: set the limit to all packages'
    print '         [pkgid:]powerval e.g., 140, 1:120'
    print ''
    print 'If no option is specified, run the test pattern.'
    print ''


def report_powerlimits():
    l = rr.get_powerlimits()
    for k in l.keys():
        if l[k]['enabled']:
            print k, 'curW:', l[k]['curW'], 'maxW:', l[k]['maxW']

def run_powercap_testbench():
    # hard-coded for Haswell E5-2699v2 dual socket
    print rr.get_powerdomains()
    report_powerlimits()

    w = 10
    rr.set_powerlimit_pkg(120)
    time.sleep(w)
    rr.set_powerlimit_pkg(80)
    time.sleep(w)
    rr.set_powerlimit(130, 'package-1')
    time.sleep(w)
    rr.set_powerlimit_pkg(145)

def test_conv():
    lns = ['package-1', 'package-3/dram',  'package-2/core']

    for ln in lns:
        sn  = rr.to_shortdn(ln)
        ln2 = rr.to_longdn(sn)
        if ln == ln2:
            print 'passed: ',
        else:
            print 'failed: ',
        print ln, sn, ln2

def test_map():
    pds = rr.create_powerdomains_cpuids()

    for pd in pds:
        print pd, pds[pd]

def unittest(m):
    if m == 'conv':
        test_conv()
    elif m == 'map':
        test_map()

if __name__ == '__main__':
    rr = rapl_reader()

    if not rr.initialized():
        print 'Error: No intel rapl sysfs found'
        sys.exit(1)

    shortopt = "h"
    longopt = ['getpd', 'getplim', 'setplim=', 'show', 'limitp=', 'testbench', 'doc', 'test=' ]
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   shortopt, longopt)

    except getopt.GetoptError, err:
        print err
        usage()
        sys.exit(1)

    for o, a in opts:
        if o in ('-h'):
            usage()
            sys.exit(0)
        elif o in ("--test"):
            unittest(a)
            sys.exit(0)
        elif o in ("--doc"):
            help(rapl_reader)
            sys.exit(0)
        elif o in ("--testbench"):
            print 'Start: testbench'
            run_powercap_testbench()
            print 'Stop: testbench'
            sys.exit(0)
        elif o in ("--getpd"):
            print rr.get_powerdomains()
            sys.exit(0)
        elif o in ("--getplim", "--show"):
            report_powerlimits()
            sys.exit(0)
        elif o in ("--setplim", "--limitp"):
            v = float(a)
            rr.set_powerlimit_pkg(v)
            report_powerlimits()
            sys.exit(0)

    rr.start_energy_counter()
    for i in range(0,3):
        time.sleep(1)
        s = rr.sample_and_json(accflag=True)
        print s
    rr.stop_energy_counter()
    s = rr.total_energy_json()
    print s

    sys.exit(0)
