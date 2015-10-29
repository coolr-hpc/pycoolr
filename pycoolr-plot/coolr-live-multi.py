#!/usr/bin/env python

import sys, os, re
import json
import time
import zlib,base64
import getopt

outputfn = 'multinodes.json'
nodes = ''


def usage():
    print ''
    print 'Usage: coolr-live-multi.py [options] config'
    print ''
    print '[options]'
    print ''
    print '--outputfn fn: specify output fiflename (default:%s)' % outputfn
    print '--nodes nodes: list of the nodes. comma separated (default:allnodes)'
    print ''

shortopt = "h"
longopt = ['output=','nodes=']
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
    elif o in ("--output"):
        outputfn=a

configfn=args[0]

with open(configfn) as f:
    cfg = json.load(f)

try:
    logf = open(outputfn, 'w', 0) # unbuffered write
except:
    print 'unable to open', outputfn


def querydataj(cmd='', decompress=False):
    f = os.popen("%s" % (cmd), "r")
    lines=[]
    while True:
        l = f.readline()
        if not l:
            break
        lines.append(l)
    f.close()

    jtext = []
    for l in lines:
        if decompress:
            tmp=zlib.decompress(base64.b64decode(l))
            for ltmp in tmp.split():
                jtext.append(ltmp)
        else:
            jtext.append(l)

    ret = [] # return an array of dict objects
    for jt in jtext:
        try:
            j = json.loads(jt)
        except ValueError, e:
            continue
        ret.append(j)

    return ret

lastdbid=0
cmd=cfg['dbquerycmd']

npkg=2 # hardcode for now

allnodes={}  # power data for now

while True:
    t1=time.time()
    if lastdbid > 0:
        j = querydataj("%s --gtidx=%d" % (cmd, lastdbid))
    else:
        j = querydataj(cmd)

    for e in j:
        # print e
        if j.has_key('node'):
            node = j['node']
            if allnodes.has_key(node):
                # total, pkg, dram, limit
                allnodes[node]['total']=j['power']['total']
                for pkgid in range(npkg):
                    allnodes[node]['total']=j['power']['total']
                    


    t2=time.time()
    print 'time on data ack:', t2-t1


    if len(j) > 0:
        lastdbid = int(j[-1]['dbid'])
        print '===',lastdbid
    time.sleep(1)

