        elif e['node'] == targetnode and e['sample'] == 'application':
            t = e['time'] - params['ts']
            params['cur'] = t # this is used in update()
            v = e['#TE_per_sec'] # XXX
            appperf_lr.add(t,v)
            pl_appperf.update(params, appperf_lr)
