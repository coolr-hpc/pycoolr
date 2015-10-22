#!/usr/bin/env python

#
# to retrieve power data from the beacon bridge
#

import sys, os, time
import sqlite3 as lite
import json

# default: retrieve only data inserted within 3 secs
nsec = 3
oldt = time.time() - nsec

if len(sys.argv) > 1:
    oldt = float(sys.argv[1])

con = lite.connect('/dev/shm/node_power.sql')

with con:
    cur = con.cursor()

    cur.execute("SELECT * FROM Data Where Time > %lf ORDER BY TIME;" % oldt)

    rows = cur.fetchall()

    for row in rows:
        print row[2]

sys.exit(0)
