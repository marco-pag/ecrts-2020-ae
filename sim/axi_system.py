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

###################################################################################################

# HW-tasks
BURST_DEF = 16
PHI_TASK_DEF = 6

# Interconnects
D_INT_ADDR = 10
D_INT_DATA = 10
D_INT_BRESP = 10
T_HOLD_ADDR = 1
T_HOLD_DATA = 1
T_HOLD_BRESP = 1
PHI_INT_DEF = 1

# PS
D_PS_READ = 25
D_PS_WRITE = 25

# TRANSACTION TIME
T_TRANS = 150

# 100 MHz
CLK_RATE = 100 * 10**6

###################################################################################################

def clks_to_ms(clks):
    return (clks / CLK_RATE) * 10**3

def ms_to_clks(ms):
    return (ms * CLK_RATE) / 10**3

###################################################################################################

class HwTask(object):
    '''
    HW-task object
    '''
    def __init__(self, phi = PHI_TASK_DEF, burst_size = BURST_DEF):
        self.phi = phi
        self.burst_size = burst_size
        
        self.trans_r = 0
        self.trans_w = 0
        self.c_time = 0
        self.period = 0
        
    def __str__(self):
        return 'C: {: <20} T: {: <20} S: {: <20} TR: {: <20} TW: {: <20}\n'.format(
            self.c_time, self.period, self.period - self.c_time, self.trans_r, self.trans_w
        )


class Interconnect(object):
    '''
    AXI Interconnect object
    '''
    def __init__(self, phi = PHI_INT_DEF, d_addr = D_INT_ADDR, d_data = D_INT_DATA, d_bresp = D_INT_BRESP,
                t_hold_addr = T_HOLD_ADDR, t_hold_data = T_HOLD_DATA, t_hold_bresp = T_HOLD_BRESP):
        self.phi = phi
        self.d_addr = d_addr
        self.d_data = d_data
        self.d_bresp = d_bresp
        self.t_hold_addr = t_hold_addr
        self.t_hold_data = t_hold_data
        self.t_hold_bresp = t_hold_bresp
    

class System(object):
    '''
    AXI system comprising a hierarchy of Interconnects and HW-tasks
    Simple and inefficient implementation meant to be easy to read
    '''
    def __init__(self, topology, d_ps_read = D_PS_READ, d_ps_write = D_PS_WRITE):       
        self._topology = topology
        self._workload = topology.workload
        self._d_ps_read = d_ps_read
        self._d_ps_write = d_ps_write
        self._resp_times = None
        
    def check_feasible(self):
        if self._resp_times is None:
            self.get_resp_times()
            
        for task_i, task in enumerate(self._workload.tasks):
            if self._resp_times[task_i] > task.period:
                return [False, task_i]
        
        return [True, None]
    
    def _get_d_nocont_r(self, inter_idx, task_idx):
        # Get level and add 1 for current interconnect
        level = len(self._topology.get_inters_below(inter_idx)) + 1
        inter = self._workload.inters[inter_idx]
        
        d_ncont_r = level * (inter.t_hold_addr + inter.d_addr) \
                    + self._d_ps_read \
                    + level * inter.d_data \
                    + self._workload.tasks[task_idx].burst_size
                    
        return d_ncont_r
        
    def _get_d_nocont_w(self, inter_idx, task_idx):
        # Get level and add 1 for current interconnect
        level = len(self._topology.get_inters_below(inter_idx)) + 1
        inter = self._workload.inters[inter_idx]
        
        d_ncont_w = level * (inter.t_hold_addr + inter.d_addr) \
                    + self._workload.tasks[task_idx].burst_size * inter.t_hold_data \
                    + self._d_ps_write \
                    + level * (inter.d_data + inter.d_bresp)
                    
        return d_ncont_w
        
    def get_resp_times(self, verbose = False):
        self._resp_times = []
        # For each task
        for task_i, task in enumerate(self._workload.tasks):
            tasks_acc = []
            n_r_acc = task.trans_r
            n_w_acc = task.trans_w
            
            # Get task's Interconnect
            inter_i = self._topology.tasks_adj[task_i]
            inter = self._workload.inters[inter_i]

            if verbose:
                print('Task {} connected to: Interconnect {}'.format(task_i, inter_i))
            #print('d_nocont_r {}'.format(d_nocont_r))
            #print('d_nocont_w {}'.format(d_nocont_w))

            # Delay coming from interfering transactions
            d_r_acc = 0
            d_w_acc = 0
            
            # Traverse the Interconnects from current interconnect to root
            for inter_j in [inter_i] + self._topology.get_inters_below(inter_i):
                eta_r_acc = 0
                eta_w_acc = 0
                phi_acc = 0
                tasks_eta = []
                
                if verbose:
                    print('\tCrossing Interconnect {}'.format(inter_j))
                
                # Populate the list of tasks that contributes to phi
                # i.e,, the tasks directly connected to current Interconnect
                tasks_phi = self._topology.get_tasks_by_inter(inter_j)
                if task_i in tasks_phi:
                    assert inter_j == inter_i
                    tasks_phi.remove(task_i)
                
                # Populate the list of tasks that contribute to eta
                # i.e., task's whose transactions traverse the current Interconnect
                # *invariant*: tasks_phi is a *subset* of tasks_eta
                inters_above = [inter_j] + self._topology.get_inters_above(inter_j)
                for inter_k in inters_above:
                    tasks_eta.extend(self._topology.get_tasks_by_inter(inter_k))
                
                # Remove from the set of eta tasks the tasks that contributed to the previous step
                tasks_eta.remove(task_i)
                tasks_eta = [task_j for task_j in tasks_eta if task_j not in tasks_acc]

                # Accumulate phi for directly connected tasks
                for task_pi in tasks_phi:
                    phi_acc += np.minimum(self._workload.tasks[task_pi].phi, inter.phi)
                
                #  Accumulate phi for directly connected interconnects
                for inter_dci in self._topology.get_inters_above_dc(inter_j):
                    phi_acc += self._workload.inters[inter_dci].phi
                
                # Calculate and accumulate eta
                for task_ei in tasks_eta:
                    interf_trans = np.ceil(task.period / self._workload.tasks[task_ei].period + 1).astype(int)
                    eta_r_acc += interf_trans * self._workload.tasks[task_ei].trans_r
                    eta_w_acc += interf_trans * self._workload.tasks[task_ei].trans_w
                    
                # Calculate interfering transactions at current hierarchical level
                y_r = np.minimum(n_r_acc * phi_acc, eta_r_acc)
                y_w = np.minimum(n_w_acc * phi_acc, eta_w_acc)
                
                # Get transactions delay in isolation
                d_nocont_r = self._get_d_nocont_r(inter_j, task_i)
                d_nocont_w = self._get_d_nocont_w(inter_j, task_i)
                
                # Multiply the number of interfering transactions with the no-contention delays to root
                d_r = d_nocont_r * y_r
                d_w = d_nocont_w * y_w
                
                # Accumulate the dealy
                d_r_acc += d_r
                d_w_acc += d_w
                
                # Update for next cycle
                tasks_acc += tasks_eta
                n_r_acc += y_r
                n_w_acc += y_w
        
            # Compute and append task's response time
            d_nocont_r = self._get_d_nocont_r(inter_i, task_i)
            d_nocont_w = self._get_d_nocont_w(inter_i, task_i)
            
            d_r_tot = task.trans_r * d_nocont_r + d_r_acc
            d_w_tot = task.trans_w * d_nocont_w + d_w_acc
            self._resp_times.append(d_r_tot + task.c_time + d_w_tot)
            
        return list(self._resp_times)


###################################################################################################

if __name__ == '__main__':
    pass
