'''
Artifact evaluation code for the paper:
Francesco Restuccia, Marco Pagani, Alessandro Biondi, Mauro Marinoni, and Giorgio Buttazzo,
"Modeling and Analysis of Bus Contention for Hardware Accelerators in FPGA SoCs",
In Proceedings of the 32nd Euromicro Conference on Real-Time Systems (ECRTS 2020), July 7-10, 2020.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.

@author: Marco Pag
'''

###################################################################################################

import numpy as np
from abc import ABC, abstractmethod

import axi_system as sys
import taskgen

###################################################################################################

class Workload(ABC):
    '''
    HW-tasks workload, for each HW-tasks generate internal parameters
    '''
    def __init__(self, num_tasks, phi_tasks = sys.PHI_TASK_DEF,
                 phi_inters = sys.PHI_INT_DEF, burst_size = sys.BURST_DEF):
        self._phi_tasks = phi_tasks
        self._phi_inters = phi_inters
        self._burst_size = burst_size

        self._inters = None
        self._tasks = [sys.HwTask(phi_tasks, burst_size) for _ in range(num_tasks)]
    
    def __str__(self):
        rout = 'Tasks\n'
        for i, task in enumerate(self._tasks):
            rout += str(i) + ':\t\t' + str(task)
            
        return rout
    
    def set_inters(self, num_inters):
        assert num_inters <= len(self._tasks)
        self._inters = [sys.Interconnect(self._phi_inters) for _ in range(num_inters)]
    
    @abstractmethod
    def generate(self):
        pass
    
    @property
    def num_tasks(self):
        return len(self._tasks)
    
    @property
    def tasks(self):
        return self._tasks
    
    @property
    def num_inters(self):
        return len(self._inters)
    
    @property
    def inters(self):
        return self._inters
    

###################################################################################################


class DummyWorkload(Workload):
    '''
    Just for testing
    '''
    def __init__(self, num_tasks):
        super().__init__(num_tasks)
        
    def generate(self):
        pass


###################################################################################################


class RandomFixedWorkload(Workload):
    '''
    Generate T_i, C_i using fixed rand sum. Then
    '''
    slack_func = lambda task: task.period - task.c_time
    trans_func = lambda task: task.trans_r + task.trans_w

    slack_asc = {
        'key'       : slack_func,
        'reverse'   : False
    }
    
    slack_dsc = {
        'key'       : slack_func,
        'reverse'   : True
    }

    def __init__(self, num_tasks):
        super().__init__(num_tasks)
        
    def generate(self, min_period, max_period, c_to_tr_ratio, utilization, ordering, rw_ratio = None):
        assert(c_to_tr_ratio <= 1)
        
        opts = {
            'num_tasks'    : self.num_tasks,
            'utilization'  : utilization,
            'num_sets'     : 1,
            'period_min'   : min_period,
            'period_max'   : max_period,
            'period_gran'  : 1,
            'period_distr' : 'logunif',
            'round_c'      : True
        }
        
        # Generate a single task-set using random fixed sum
        # Output tuples: <0:'Ugen', 1:'U', 2:'T', 3:'C'>
        tasksets = taskgen.gen_tasksets_from_dict(opts)
        
        for i, task in enumerate(self._tasks):
            task.period = tasksets[0][i][2].astype(int)
            task.c_time = tasksets[0][i][3].astype(int)
            
            # Generate the number of task's transactions by scaling down the maximum
            # number of transactions that the task can do within a single period
            # (considering a fixed transaction time sys.T_TRANS).
            trans_max = np.floor(task.c_time / sys.T_TRANS)
            trans_tot = np.floor(trans_max * c_to_tr_ratio).astype(int)
            
            if rw_ratio is None:
                rw_ratio = np.random.uniform(0.4, 0.6)
            
            task.trans_r = np.rint(trans_tot * rw_ratio).astype(int)
            task.trans_w = np.rint(trans_tot * (1 - rw_ratio)).astype(int)

        # Order tasks
        self._tasks.sort(key = ordering['key'], reverse = ordering['reverse'])

###################################################################################################

if __name__ == '__main__':
    pass

