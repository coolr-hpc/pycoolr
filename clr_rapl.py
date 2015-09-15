#!/usr/bin/env python
#
# coolr rapl related codes
#
# This code requires the intel_powerclamp module.
#
# Contact: Kazutomo Yoshii <ky@anl.gov>
#

import os, sys, re, time

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

    def initialized(self):
        return self.init

    def shortenkey(self,str):
        return str.replace('package-','p')

#        for k in sorted(self.dirs.keys()):
#            print k, self.max_energy_range_uj_d[k]


    def readenergy(self):
        if not self.init:
            return

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
        if not self.init:
            return

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


if __name__ == '__main__':

    rr = rapl_reader()

    if rr.initialized():
        for i in range(0,3):
            print '#%d reading rapl' % i
            e1 = rr.readenergy()
            time.sleep(1)
            e2 = rr.readenergy()
            p = rr.calcpower(e1,e2)
            for k in sorted(p):
                print k, p[k]
        print
    else:
        print 'Error: No intel rapl sysfs found'

