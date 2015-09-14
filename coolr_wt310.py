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

    # default setting. to query, :NUM:NORM:ITEM1? for exampe
    # 1: Watt hour, 2: Current, 3: Active Power, 4: Apparent Power 
    # 5: Reactive Power, 6: Power factor

    def sample(self):
        a = self.readvals()
        ret = {}
        ret['WH'] = a[0] # NOTE: the item no minus one
        ret['P']  = a[2]
        ret['PF'] = a[5]
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


if __name__ == '__main__':

    cmd = ''
    if len(sys.argv) >= 2:
        cmd = sys.argv[1]

    wt310 = coolr_wt310_reader()

    if wt310.open():
        sys.exit(1)

    wt310.start()

    if len(cmd) > 0:
        print wt310.get(cmd)
        sys.exit(0)

    while True:
        s =  wt310.sample()

        #joules = float(s['WH']) * 3600.0
        print '%.2lf' % time.time(),
        #print '%lf' % joules,
        print s['P'], s['PF'],
        print

        time.sleep(1)
