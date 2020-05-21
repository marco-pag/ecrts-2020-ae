'''
Artifact evaluation code for the paper:
Francesco Restuccia, Marco Pagani, Alessandro Biondi, Mauro Marinoni, and Giorgio Buttazzo,
"Modeling and Analysis of Bus Contention for Hardware Accelerators in FPGA SoCs",
In Proceedings of the 32nd Euromicro Conference on Real-Time Systems (ECRTS 2020), July 7-10, 2020.

The following code has been adapted from:
A taskset generator for experiments with real-time task sets

Copyright 2010 Paul Emberson, Roger Stafford, Robert Davis. 
All rights reserved.

Redistribution and use in source and binary forms, with or without 
modification, are permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY EXPRESS 
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES 
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO 
EVENT SHALL THE AUTHORS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, 
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT 
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE 
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are 
those of the authors and should not be interpreted as representing official 
policies, either expressed or implied, of Paul Emberson, Roger Stafford or 
Robert Davis.

Includes Python implementation of Roger Stafford's randfixedsum implementation
http://www.mathworks.com/matlabcentral/fileexchange/9700
Adapted specifically for the purpose of taskset generation with fixed
total utilisation value

Please contact paule@rapitasystems.com or robdavis@cs.york.ac.uk if you have 
any questions regarding this software.
'''

import numpy

def StaffordRandFixedSum(n, u, nsets):
    #deal with n=1 case
    if n == 1:
        return numpy.tile(numpy.array([u]),[nsets,1])
    
    k = numpy.floor(u)
    s = u
    step = 1 if k < (k-n+1) else -1
    s1 = s - numpy.arange( k, (k-n+1)+step, step )
    step = 1 if (k+n) < (k-n+1) else -1
    s2 = numpy.arange( (k+n), (k+1)+step, step ) - s

    tiny = numpy.finfo(float).tiny
    huge = numpy.finfo(float).max

    w = numpy.zeros((n, n+1))
    w[0,1] = huge
    t = numpy.zeros((n-1,n))

    for i in numpy.arange(2, (n+1)):
        tmp1 = w[i-2, numpy.arange(1,(i+1))] * s1[numpy.arange(0,i)]/float(i)
        tmp2 = w[i-2, numpy.arange(0,i)] * s2[numpy.arange((n-i),n)]/float(i)
        w[i-1, numpy.arange(1,(i+1))] = tmp1 + tmp2;
        tmp3 = w[i-1, numpy.arange(1,(i+1))] + tiny;
        tmp4 = numpy.array( (s2[numpy.arange((n-i),n)] > s1[numpy.arange(0,i)]) )
        t[i-2, numpy.arange(0,i)] = (tmp2 / tmp3) * tmp4 + (1 - tmp1/tmp3) * (numpy.logical_not(tmp4))

    m = nsets
    x = numpy.zeros((n,m))
    rt = numpy.random.uniform(size=(n-1,m)) #rand simplex type
    rs = numpy.random.uniform(size=(n-1,m)) #rand position in simplex
    s = numpy.repeat(s, m);
    j = numpy.repeat(int(k+1), m);
    sm = numpy.repeat(0, m);
    pr = numpy.repeat(1, m);

    for i in numpy.arange(n-1,0,-1): #iterate through dimensions
        e = ( rt[(n-i)-1,...] <= t[i-1,j-1] ) #decide which direction to move in this dimension (1 or 0)
        sx = rs[(n-i)-1,...] ** (1/float(i)) #next simplex coord
        sm = sm + (1-sx) * pr * s/float(i+1)
        pr = sx * pr
        x[(n-i)-1,...] = sm + pr * e
        s = s - e
        j = j - e #change transition table column if required

    x[n-1,...] = sm + pr * s
    
    #iterated in fixed dimension order but needs to be randomised
    #permute x row order within each column
    for i in range(0,m):
        x[...,i] = x[numpy.random.permutation(n),i]

    return numpy.transpose(x);

def gen_periods(n, nsets, min_p, max_p, gran, dist):
    if dist == "logunif":
        periods = numpy.exp(numpy.random.uniform(low=numpy.log(min_p), high=numpy.log(max_p+gran), size=(nsets,n)))
    elif dist == "unif":
        periods = numpy.random.uniform(low=min_p, high=(max_p+gran), size=(nsets,n))
    else:
        return None
    periods = numpy.floor(periods / gran) * gran

    return periods

def gen_tasksets_from_dict(opts = None):
    if opts is None: opts = {
        'num_tasks'    : 10,
        'utilization'  : 5,
        'num_sets'     : 2,
        'period_min'   : 10,
        'period_max'   : 100,
        'period_gran'  : 1,
        'period_distr' : 'logunif',
        'round_c'      : True
    }

    tasksets = []
    x = StaffordRandFixedSum(opts['num_tasks'], opts['utilization'], opts['num_sets'])
    periods = gen_periods(opts['num_tasks'], opts['num_sets'], opts['period_min'], opts['period_max'], opts['period_gran'], opts['period_distr'])
    #iterate through each row (which represents utils for a taskset)
    for i in range(numpy.size(x, axis=0)):
        C = x[i] * periods[i]
        if opts['round_c']:
            C = numpy.round(C, decimals=0)
        
        # Numpy array, each row is a task t:
        # <'Ugen' : taskset[t][0], 'U' : taskset[t][1], 'T' : taskset[t][2], 'C' : taskset[t][3]>
        # the actual utilization equal to C/T which will differ from U generated if the round-C option is used
        taskset = numpy.c_[x[i], C / periods[i], periods[i], C]
        tasksets.append(taskset)
        
    return tasksets

def print_taskset_plain(taskset):
    for task in taskset:
        print('Ugen: {:.5f}\t U: {:.5f}\t T: {:.5f}\t C: {:.5f}'.format(task[0], task[1], task[2], task[3]))

if __name__ == "__main__":
    opts = {
        'num_tasks'    : 10,
        'utilization'  : 1,
        'num_sets'     : 1,
        'period_min'   : 10,
        'period_max'   : 1000,
        'period_gran'  : 1,
        'period_distr' : 'logunif',
        'round_c'      : True
    }
    tasksets = gen_tasksets_from_dict(opts)
    for taskset in tasksets:
        #print_taskset(taskset, '%(Ugen)f %(U)f %(C)f %(T)d')
        print_taskset_plain(taskset)
        print("")

