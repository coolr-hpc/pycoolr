#!/usr/bin/env python

# this is ad-hoc demo script, which will be replaced by coolrmon.py later
#
# realtime temp graph of sensor reading at duteros
#
# Kaz Yoshii <ky@anl.gov>

import sys, os, re
import json
import time
import numpy as np
import matplotlib.pyplot as plt
import pylab
from collections import deque
import matplotlib.cm as cm


if len(sys.argv) < 2:
    print 'Usage: demo.py config'
    sys.exit(1)
    
configfile = sys.argv[1]

with open(configfile) as f:
    config = json.load(f)

print 'Config :', configfile
    

plotapp = False
#maxpoints = 360
maxpoints = 120
interval = 1

#
#

fig=plt.figure( figsize=(15,10) )

i=0
x=list()
y=list()

plt.ion()  # turn interactive mode on
plt.show()

try:
    logf = open( 'data.log', 'w', 0 ) # unbuffered write
except:
    print 'unable to open data.log'

def querydata():
    f = os.popen(config["querycmd"], "r")
    while True:
        line = f.readline()
        if not line:
            break
        res = line.split()
    f.close()
    return res



def querydataj(cmd=''):
    f = os.popen("%s %s" % (config["querycmd"],cmd), "r")
    ret = [] # return an array of dict objects

    while True:
        l = f.readline()
        if not l:
            break
        try:
            j = json.loads(l)
        except ValueError, e:
            break
        ret.append(j)
        logf.write(l)
    f.close()

    return ret


def queryexternalj(cmd=''):
    f = os.popen("%s %s" % (config["external"],cmd), "r")
    ret = [] # return an array of dict objects

    while True:
        l = f.readline()
        if not l:
            break
        ret.append(json.loads(l))
        logf.write(l)
    f.close()

    return ret

#
#

x = []

info = querydataj('--info')[0]
npkgs = info['npkgs']  # assume npkg does not change during the measurement

nans = [ np.nan for i in range(0,maxpoints) ]

uptimeq = deque(nans)

#
acpwrq = deque(nans)

# 
meanqs  = [ deque(nans) for i in range(0,npkgs) ]
stdqs   = [ deque(nans) for i in range(0,npkgs) ]

dgemm_meanqs  = [ deque(nans) for i in range(0,npkgs) ]
dgemm_stdqs   = [ deque(nans) for i in range(0,npkgs) ]

freq_meanqs  = [ deque(nans) for i in range(0,npkgs) ]
# freq_stdqs   = [ deque(nans) for i in range(0,npkgs) ]


powerqs = [ deque(nans) for i in range(0,npkgs) ]
drampowerqs = [ deque(nans) for i in range(0,npkgs) ]
totalpowerqs = deque(nans)

plimqs =  [ deque(nans) for i in range(0,npkgs) ]

# array to hold per-package energy value
prev_e = [ 0 for i in range(0,npkgs) ]

prev_dram_e = [ 0 for i in range(0,npkgs) ]

maxenergyuj = [ 0 for i in range(0,npkgs) ]

for i in range(0, npkgs):
    k = 'p%d' % i
    maxenergyuj[i] = info['max_energy_uj'][k]

sample = querydataj("--sample")
s_temp = sample[0]
s_energy = sample[1]["energy"]
s_freq = sample[2]

# to calculate the average power we need the previous value

start_t = s_temp['time']
prev_t = start_t
for i in range(0, npkgs):
    k = 'p%d' % i
    prev_e[i] = s_energy[k]
    if config["dramrapl"] == "yes":
        k = 'p%d/dram' % i
        prev_dram_e[i] = s_energy[k]

cnames= [ 'blue', 'green' ]


while True:
    #
    # querying
    #
    
    sample = querydataj("--sample")
    s_temp = sample[0]
    s_energy = sample[1]["energy"]
    s_powercap = sample[1]["powercap"]
    s_freq = sample[2]
    if len(sample) == 4:
        s_acpi = sample[3]

    #
    #
    
    cur_t = s_temp['time']
    rel_t =  cur_t - start_t 
    uptimeq.popleft()
    uptimeq.append( rel_t )
    # print uptimeq

    totalpower=0.0

    for i in range(0,npkgs): 
        p = 'p%d' % i
        vm = s_temp[p]['mean']
        vs = s_temp[p]['std']

        meanqs[i].popleft()
        meanqs[i].append(vm) 
        stdqs[i].popleft()
        stdqs[i].append(vs)

        fm = s_freq[p]['mean']

        freq_meanqs[i].popleft()
        freq_meanqs[i].append(fm) 

        cur_pkg_e = s_energy[p]
        edelta = cur_pkg_e - prev_e[i]
        if edelta < 0 :
            edelta += maxenergyuj[i]
        tdelta = cur_t - prev_t
        #print cur_t, prev_t
        powerwatt = edelta / (1000*1000.0) / tdelta
        totalpower=totalpower+powerwatt
        powerqs[i].popleft()
        powerqs[i].append(powerwatt)
        prev_e[i] = cur_pkg_e
        #print 'pkgpower%d=%lf' % (i, powerwatt), 

        if config["dramrapl"]:
            cur_dram_e = s_energy[p + '/dram']
            edelta = cur_dram_e - prev_dram_e[i]
            if edelta < 0 :
                edelta += maxenergyuj[i]  # XXX: fix this. dram may have different max value
            powerwatt = edelta / (1000*1000.0) / tdelta
            totalpower=totalpower+powerwatt
            drampowerqs[i].popleft()
            drampowerqs[i].append(powerwatt)
            prev_dram_e[i] = cur_dram_e
            #print 'drampower%d=%lf' % (i, powerwatt), 

        plimqs[i].popleft()
        plimqs[i].append(s_powercap[p])


    if config["drawexternal"] == "yes":
        s_ac = queryexternalj("--sample")[0]
        acpwrq.popleft()
        acpwrq.append(float(s_ac["power"]))

    if config["drawacpipwr"] == "yes" :
        acpwrq.popleft()
        acpwrq.append(s_acpi['power'])

    # print 'totalpower=%lf' % totalpower
    totalpowerqs.popleft()
    totalpowerqs.append( totalpower )

    prev_t = cur_t

    # update the plot
    plt.clf() 

    # common
    l_uptime=list(uptimeq)

    #
    #
    subplotidx = 1

    #
    #
    plt.subplot(2,4,subplotidx)
    subplotidx = subplotidx +1
    plt.axis([rel_t - maxpoints*interval, rel_t, config["mintemp"], config["maxtemp"]]) # [xmin,xmax,ymin,ymax]
#    plt.axhspan( 70, maxtemp, facecolor='#eeeeee', alpha=0.5)

    for pkgid in range(0, npkgs):
        l_meanqs=list(meanqs[pkgid])
        plt.plot(l_uptime, l_meanqs , scaley=False, label='CPUPKG%d'%pkgid )
        plt.errorbar(l_uptime, l_meanqs, yerr=list(stdqs[pkgid]), lw=.2, color=cnames[pkgid], label='' )

    plt.xlabel('Uptime [S]')
    plt.ylabel('Core temperature [C]')

    #
    # assume drawacpipwr and drawexternal is exclusive
    if config["drawacpipwr"] == "yes" or config["drawexternal"]: 
        plt.subplot(2,4,subplotidx)
        subplotidx = subplotidx + 1
        plt.axis([rel_t - maxpoints*interval, rel_t, 20, config["acpwrmax"]]) # [xmin,xmax,ymin,ymax]

        l_uptime=list(uptimeq)

        l_acpwrqs=list(acpwrq)
        plt.plot(l_uptime, l_acpwrqs, 'k', scaley=False)

        l_totalpowerqs=list(totalpowerqs)
        plt.plot(l_uptime, l_totalpowerqs, 'k--', scaley=False )

        plt.xlabel('Uptime [S]')
        plt.ylabel('Power [W] - AC Power and RAPL total')

    #
    #
    plt.subplot(2,4,subplotidx)
    subplotidx = subplotidx + 1
    plt.axis([rel_t - maxpoints*interval, rel_t, config["pwrmin"], config["pwrmax"]]) # [xmin,xmax,ymin,ymax]
#    plt.axhspan( 115, 120, facecolor='#eeeeee', alpha=0.5)

    l_uptime=list(uptimeq)
    for pkgid in range(0, npkgs):
        plt.plot(l_uptime, list(plimqs[pkgid]), scaley=False, color='red' )
        l_powerqs=list(powerqs[pkgid])
        plt.plot(l_uptime, l_powerqs, scaley=False, label='PKG%d'%pkgid, color=cnames[pkgid] )

        if config["dramrapl"] == "yes": 
            l_drampowerqs=list(drampowerqs[pkgid])
            plt.plot(l_uptime, l_drampowerqs, scaley=False, label='DRAM%d'%pkgid, color=cnames[pkgid], ls='-' )

    plt.xlabel('Uptime [S]')
    plt.ylabel('RAPL Power [W]')

    #
    #
    plt.subplot(2,4,subplotidx)
    subplotidx = subplotidx + 1
    plt.axis([rel_t - maxpoints*interval, rel_t, config["freqmin"], config["freqmax"]]) # [xmin,xmax,ymin,ymax]
    plt.axhspan( config["freqnorm"], config["freqmax"], facecolor='#eeeeee', alpha=0.5)

    for pkgid in range(0, npkgs):
        l_uptime=list(uptimeq)
        l_freq_meanqs=list(freq_meanqs[pkgid])
        plt.plot(l_uptime, l_freq_meanqs , scaley=False, label='PKG%d'%pkgid )
#        plt.errorbar(l_uptime, l_freq_meanqs, yerr=list(freq_stdqs[pkgid]), lw=.2, color=cnames[pkgid], label='' ) # too noisy
    plt.xlabel('Uptime [S]')
    plt.ylabel('CPU Frequency [GHz]')

    #
    # freq bar graph
    # XXX: quick dirty for now
    plt.subplot(2,4,subplotidx)
    subplotidx = subplotidx + 1
    nbars = config["ncpu"]*4
    plt.axis([0, nbars , config["freqmin"], config["freqmax"]])

    offset = 0
    for pkgid in range(0, npkgs):
        ind = np.arange(nbars/2) + offset
        tmpy = []
        p = 'p%d' % pkgid
        for kc in sorted(s_freq[p].keys()):
            if kc[0] == 'c':
                tmpy.append(s_freq[p][kc])
                offset += 1
        plt.bar( ind, tmpy, width = .6, color=cnames[pkgid], edgecolor='none' )
                
    #
    # app

    if plotapp:
        try:
            dgemm = querydataj('dgemm')

            for pkgid in range(0, npkgs):
                gflops = []
                for i in range(0,ncpu):
                    k = 'dgemm%d'%(i+(pkgid*ncpu))
                    if dgemm.has_key(k):
                        gflops.append( float(dgemm[k]) )
                    else:
                        print 'why ', k
                    k = 'dgemm%d'%(i+((pkgid+2)*ncpu))
                    if dgemm.has_key(k):
                        gflops.append( float(dgemm[k]) )
                    else:
                        print 'why ', k
                        
            gflops_mean= np.mean(gflops)
            #print pkgid, gflops_mean
            glopps_std = np.std(gflops)
            #print pkgid, gflops_mean, glopps_std
            dgemm_meanqs[pkgid].popleft()
            dgemm_meanqs[pkgid].append(gflops_mean)
            dgemm_stdqs[pkgid].popleft()
            dgemm_stdqs[pkgid].append(glopps_std)
        except:
            dgemm_meanqs[pkgid].popleft()
            dgemm_meanqs[pkgid].append(np.nan)
            dgemm_stdqs[pkgid].popleft()
            dgemm_stdqs[pkgid].append(np.nan)

        plt.subplot(2,4,subplotidx)
        subplotidx = subplotidx + 1

        #    plt.axis([rel_t - maxpoints*interval, rel_t, 7.5, 9.0]) # [xmin,xmax,ymin,ymax]                                                        
        for pkgid in range(0, npkgs):
            l_uptime=list(uptimeq)
            plt.plot(l_uptime, dgemm_meanqs[pkgid] , label='CPUPKG%d'%pkgid )
            plt.errorbar(l_uptime, dgemm_meanqs[pkgid], yerr=list(dgemm_stdqs[pkgid]), lw=.2, color=cnames[pkgid], label='' )
            pylab.xlim( [rel_t - maxpoints*interval, rel_t ] )

        plt.xlabel('Time [S]')
        plt.ylabel('[Gflop/s]')
    

    #
    # cmap
    #
    for pkgid in range(0, 2): # this only works with dual sockets
        plt.subplot(2,4,subplotidx+pkgid)

        pn = 'p%d' % pkgid
        A = []
        for r in config["tempmap"]:
            tmp = []
            for c in r :
                if c == -1:
                    tmp.append(s_temp[pn]['pkg'])
                else:
                    tmp.append(s_temp[pn]['%d' % c])
            A.append(tmp)

        ax = plt.gca()
        cax = ax.imshow(A, cmap=cm.jet , vmin=config["mintemp"], vmax=config["maxtemp"] ,aspect=0.7, interpolation='none') # interpolation='nearest' 
        cbar = fig.colorbar( cax )
        plt.xticks( [] )
        plt.yticks( [] )
        plt.title( 'CPU PKG%d' % pkgid)

    subplotidx = subplotidx + 2

    #
    #

    plt.subplot(2,4,subplotidx)
    subplotidx = subplotidx + 1

    def ypos(i):
        return 1.0 - 0.05*i

    plt.axis( [0,1,0,1] )
    pylab.setp(pylab.gca(), frame_on=True, xticks=(), yticks=())

    plt.plot( [ 0.1, 0.2], [0.96, 0.96], color='blue',  linewidth=2 )
    plt.plot( [ 0.1, 0.2], [0.91, 0.91], color='green', linewidth=2 )
    plt.plot( [ 0.1, 0.2], [0.86, 0.86], color='red',   linewidth=1 )
    plt.text( 0.3, ypos(1), 'CPU PKG0' )
    plt.text( 0.3, ypos(2), 'CPU PKG1' )
    plt.text( 0.3, ypos(3), 'powerlimit' )

    l=5
    plt.text( 0.1, ypos(l), 'Linux kernel : %s' % info['kernelversion'] )
    l += 1
    plt.text( 0.1, ypos(l), 'Freq driver : %s' % info['freqdriver'] )
    l += 1
# XXX
#    plt.text( 0.1, ypos(l), 'Freq governor : %s' % info['cpufreq_governor'] )
#    l += 1
#    if info['cpufreq_cur_freq'] == turbofreq:
#        plt.text( 0.1, ypos(l), 'Turboboost %.1f - %.1f GHz' % (freqnorm, freqmax) )
#    else:
#        plt.text( 0.1, ypos(l), 'Current freq. : %s Hz' % info['cpufreq_cur_freq'] )

    l += 1

    l += 1
    plt.text( 0.1, ypos(l), 'Powewcap pkg0 : %d Watt' % s_powercap['p0'] )
    l += 1
    plt.text( 0.1, ypos(l), 'Powercap pkg1 : %d Watt' % s_powercap['p1'] )

    l += 1
    l += 1
    plt.text( 0.1, ypos(l), config["mdesc1"] )
    l += 1
    plt.text( 0.1, ypos(l), config["mdesc2"] )
    l += 1
    plt.text( 0.1, ypos(l), config["mdesc3"] )
    l += 1

    #
    #
    fig.tight_layout()

    plt.draw()
    time.sleep(interval-0.1)

sys.exit(0)
