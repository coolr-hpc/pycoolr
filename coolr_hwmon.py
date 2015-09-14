#!/usr/bin/env python
#
# coolr hwmon related codes
#
# This code requires the coretemp driver for temperature reading
#
# Contact: Kazutomo Yoshii <ky@anl.gov>
#

import re, os, sys
import numpy as np
from coolr_cpuinfo import *

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



class acpi_power_meterp_reader :
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


if __name__ == '__main__':

#    print '=== ', sys._getframe().f_code.co_name
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
