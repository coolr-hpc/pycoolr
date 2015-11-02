#!/usr/bin/env python

#
# to retrieve power data from the beacon bridge
#

import sys, os, time
import sqlite3 as lite
import json
import zlib, base64
import getopt


# default: retrieve only data inserted within 3 secs
secago = 3
dbfile = '/dev/shm/node_power.sql'
gtidx=-1
compress=False
last=-1
stat=False

def usage():
    print ''
    print 'Usage: query-beep-db.py [options]'
    print ''
    print '[options]'
    print ''
    print '--dbfile=filename : specify dbfile  (default=%s)' % dbfile
    print '--secago=N : retrieve data between N sec old and now (default=%d)' % secago
    print '--gtidx=N : retrieve data whose idx is greather than N (no default)'
    print '--last=N : retrieve last N data (no default)   higher priority than --gtidx'
    print '--compress : data compressed by zlib and print base64 encoded string'
    print

shortopt = "h"
longopt = ['dbfile=', 'secago=', 'gtidx=', 'last=', 'compress', 'stat']
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
    elif o in ("--dbfile"):
        dbfile=a
    elif o in ("--secago"):
        secago=float(a)
    elif o in ("--gtidx"):
        gtidx=int(a)
    elif o in ("--compress"):
        compress=True
    elif o in ("--last"):
        last=int(a)
    elif o in ("--stat"):
        stat=True

oldt = time.time() - secago

con = lite.connect(dbfile)

with con:
    cur = con.cursor()

    if last > 0:
        cur.execute("SELECT * FROM Data Limit %d;" % last)
    elif gtidx > 0 :
        cur.execute("SELECT * FROM Data Where Id > %d Order by Id;" % gtidx)
    else:
        cur.execute("SELECT * FROM Data Where Time > %lf ORDER BY TIME;" % oldt)

    rows = cur.fetchall()

    buf = ''
    t1=0
    t2=0
    nrecs=0
    for row in rows:
        try:
            j = json.loads(row[2])
            # add dbid so that the acquisition side can keep track
            j['dbid'] = int(row[0])
            buf += json.dumps(j)
            buf += '\n'
            if t1 == 0:
                t1 = float(row[1])
            else:
                t2 = float(row[1])
            nrecs += 1
        except:
            print >> sys.stderr, 'json error:', row[2]

    if compress:
        print base64.b64encode(zlib.compress(buf,9))
    else:
        print buf,

    if stat:
        if nrecs > 1:
            print "{'sample':'query-beep-db', 'rps':%.2lf}" % (float(nrecs)/(t2-t1))

#   print len(buf)


sys.exit(0)
