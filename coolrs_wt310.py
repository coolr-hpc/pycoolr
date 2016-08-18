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
import smq
import keypress
import json
import math

class wt310_reader:

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
        # note that a's index is the item number minus one

        ret = {}
        # ret['WH'] = float(a[0])
        ret['J']  = float(a[0]) * 3600.0
        ret['P']  = float(a[2])
        ret['PF'] = float(a[5])
        return ret

    def start(self):
        #  set the update interval 100ms (fastest) 
        self.set(":RATE 100MS") 
        # set item1 watt-hour
        self.set(":NUM:NORM:ITEM1 WH,1")
        # start integration
        self.set(":INTEG:MODE NORM")
        self.set(":INTEG:TIM 2,0,0")  # 2 hours
        self.set(":INTEG:START")
        # ":INTEG:RESET" reset integration

    def reset(self):
        self.set('*RST')  # initialize the settings
        self.set(':COMM:REM ON') # set remote mode

    def stop(self):
        self.set(":INTEG:STOP")  # stop integration


import getopt

def usage():
    print ''
    print 'Usage: coolrs_wt310.py [options]'
    print ''
    print '[options]'
    print ''
    print '-i int : sampling interval in sec'
    print '-o str : output filename'
    print '-s str : start the mq producer. str is ip address'
    print '--set str : issue command'
    print '--get str : query value'
    print ''
    print 'Examples:'
    print '$ coolrs_wt310.py -i 0.2  # sample every 0.2 sec'
    print '$ coolrs_wt310.py --set=:INTEG:RESET   # reset the energy itegration'
    print '$ coolrs_wt310.py --get=:NUM:NORM:VAL? # query values'

    print ''


if __name__ == '__main__':

    interval_sec = .2
    outputfn = ''
    smqflag = False
    ipaddr = ''

    cmdmode = ''
    cmd = ''
    samplemode = False

    shortopt = "hi:o:s:"
    longopt = ["set=", "get=", "sample"]
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
        elif o in ('--sample'):
            samplemode = True
        elif o in ('--set'):
            cmdmode = 'set'
            cmd = a
        elif o in ('--get'):
            cmdmode = 'get'
            cmd = a
        elif o in ('-o'):
            outputfn = a
        elif o in ('-s'):
            smqflag = True
            ipadr = a
        else:
            print 'Unknown:', o, a
            
    #
    #

    wt310 = wt310_reader()

    if wt310.open():
        sys.exit(1)

    if samplemode:
        s = wt310.sample()
        ts = time.time()
        str = '# {"sample":"wt310", "time":%.2lf, "power":%.2lf}' % \
            (ts, s['P'])
        print str
        sys.exit(0)

    if len(cmd) > 0:
        if cmdmode == 'set':
            wt310.set(cmd)
        else:
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

    cfg = {}
    cfg["c1"] = {"label":"Time","unit":"Sec"}
    cfg["c1"] = {"label":"Energy","unit":"Joules"}
    cfg["c3"] = {"label":"Power", "unit":"Watt"}
    #cfg["c"] = {"label":"Power Factor", "unit":""}
    # print >>f, json.dumps(cfg)

    # XXX: smq is not tested
    if smqflag:
        mq = smq.producer(ipaddr)
        mq.start()
        mq.dict = cfg
        print 'Message queue is started:', ipaddr

    kp = keypress.keypress()
    kp.enable()

    s = wt310.sample()
    time.sleep(1)

    sys.stderr.write('Press "q" to terminate\n')

    while True:
        wt310.start()

        s = wt310.sample()

        ts = time.time()

        ev = s['J'] # energy
        pv = s['P'] # power

        str = '%.2lf %.2lf %.2lf' % \
            (ts, ev, pv)

        if math.isnan(ev) or math.isnan(pv):
            str = '#' + str

        print >>f, str
        f.flush()

        if smqflag:
            mq.append(str)

        time.sleep(interval_sec)

        if kp.available() and kp.readkey() == 'q':
            break

    wt310.stop()
    kp.disable()

    sys.stderr.write('done\n')
