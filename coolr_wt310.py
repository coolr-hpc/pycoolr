#!/usr/bin/env python
#
# a code to read Yokogawa wt310 via the usbtmc interface
#
# This code requires the usbtmc driver for temperature reading.
#
# /dev/usbtmc[0-9] needs to be readable for this code
#
# Contact: Kazutomo Yoshii <ky@anl.gov>
#

import re, os, sys
import time

class coolr_wt310_reader:

    def __init__(self):
        self.fd = -1

    def open(self, devfn = '/dev/usbtmc0'):
        self.fd = os.open(devfn, os.O_RDWR)
        if self.fd < 0:
            return -1

        return 0
    
    # read() and write() are low-level method
    def read(self):
        if self.fd < 0:
            return -1
        buf = os.read(self.fd, 256) # 256 bytes
        return buf

    def write(self, buf):
        if self.fd < 0:
            return -1
        n = os.write(self.fd, buf)
        return n

    # wt310 methods should call read() and write()
    def set(self, cmd):
        self.write(cmd)

    def get(self, cmd):
        self.write(cmd)
        buf = self.read()
        return buf

    # send wt310 commands

    def readvals(self):
        buf = self.get(":NUM:NORM:VAL?\n") # is \n required?
        return buf.split(',')


    def sample(self):
        a = self.readvals()
        # default setting. to query, :NUM:NORM:ITEM1? for exampe
        # 1: Watt hour, 2: Current, 3: Active Power, 4: Apparent Power 
        # 5: Reactive Power, 6: Power factor
        # a's index is the item no minus one

        ret = {}
        # ret['WH'] = float(a[0])
        ret['J'] = float(a[0]) * 3600.0
        ret['P']  = float(a[2])
        ret['PF'] = float(a[5])
        return ret

    def start(self):
        # set item1 watt-hour
        self.set(":NUM:NORM:ITEM1 WH,1")
        # start integration
        self.set(":INTEG:START")
        # ":INTEG:RESET" reset integration
        # ":RATE 100MS"  set the update rate 100ms

    def reset(self):
        self.set('*RST')  # initialize the settings
        self.set(':COMM:REM ON') # set remote mode

    def stop(self):
        self.set(":INTEG:STOP")  # stop integration


import getopt

def usage():
    print ''
    print 'Usage: coolr_wt310.py [options]'
    print ''
    print '[options]'
    print ''
    print '-i int : sampling interval in sec'
    print '-c str : command string'
    print '-o str : output string'
    print ''

if __name__ == '__main__':

    interval_sec = .5
    cmd = ''
    outputfn = ''

    shortopt = "hi:c:o:"
    longopt = []
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
        elif o in ('-i'):
            interval_sec = float(a)
        elif o in ('-c'):
            cmd = a
        elif o in ('-o'):
            outputfn = a
        else:
            print 'Unknown:', o, a
            
    #
    #

    wt310 = coolr_wt310_reader()

    if wt310.open():
        sys.exit(1)

    if len(cmd) > 0:
        print wt310.get(cmd)
        sys.exit(0)

    f = sys.stdout

    if len(outputfn) > 0:
        try:
            f = open(outputfn, 'w')
        except:
            print 'Error: failed to open', fn
            sys.exit(1)

        print 'Writing to', outputfn

    while True:
        wt310.start()

        s = wt310.sample()

        print >>f, '%.2lf' % time.time(),
        print >>f, '%.0lf' % s['J'],
        print >>f, '%.2lf' % s['P'],
        print >>f, '%.4lf' % s['PF'],
        print >>f, ''
        f.flush()

        time.sleep(interval_sec)
