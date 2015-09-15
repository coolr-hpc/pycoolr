#!/usr/bin/env python

#
# coolr graph generate that can be used for realtime rendering
#
# Contact: Kaz Yoshii <ky@anl.gov>
#

import time
import numpy as np
import matplotlib.pyplot as plt
import pylab
from collections import deque
import matplotlib.cm as cm


def graph_power(ts, pw): 
    plt.plot(ts, pw, 'k', scaley=False)

    plt.xlabel('Uptime [S]')
    plt.ylabel('Power [W]')



