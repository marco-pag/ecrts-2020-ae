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

import numpy as np
import matplotlib.pyplot as plt

import os
import concurrent.futures as fts

import axi_topology as topo
import axi_workload as work
import axi_system as sys

###################################################################################################

OUT_DIR = './data'

###################################################################################################

def test_bin_fixed_config(num_tasks, num_inters, num_tasksets, c_to_tr_points, verbose):
    #########################################
    utilization = 1
    
    task_period_min = sys.ms_to_clks(10)
    task_period_max = sys.ms_to_clks(100)
    
    c_to_tr_ratio_min = 0.1
    c_to_tr_ratio_max = 1.0
    #########################################
    print('Start\t tasks: {: <10} inters: {: <10}'.format(num_tasks, num_inters))
    
    with open('{}/log_t_{}_i_{}.txt'.format(OUT_DIR, num_tasks, num_inters), 'w') as log_file:
        # Feasibility indexes for each bus loading (transaction density) factor
        feasible = np.zeros(c_to_tr_points)
        
        # Generate a set of evenly spaced transaction density factor
        c_to_tr_ratio_set = np.linspace(c_to_tr_ratio_min, c_to_tr_ratio_max, num = c_to_tr_points)
        
        # For each transaction density factor in the set
        for i, c_to_tr_ratio in enumerate(c_to_tr_ratio_set):
            num_feasible = 0
            # Generate 'num_tasksets' tasksets
            for _ in range(num_tasksets):
                workload = work.RandomFixedWorkload(num_tasks);
                workload.generate(
                    min_period = task_period_min,
                    max_period = task_period_max,
                    c_to_tr_ratio = c_to_tr_ratio,
                    utilization = utilization,
                    ordering = work.RandomFixedWorkload.slack_asc
                )
                if verbose:
                    log_file.write(str(workload))
                    
                # Generate the topology
                topology = topo.BinaryEvenTopology(workload, num_inters, top_down = False)
                if verbose:
                    log_file.write(str(topology))
            
                system = sys.System(topology)
                fflag, _ = system.check_feasible()
                if fflag:
                    num_feasible += 1
            
            feasible[i] = num_feasible / num_tasksets
            
        log_file.write(str(feasible))
        
        # Write output file for PFG
        with open('{}/sched_t_{}_i_{}.csv'.format(OUT_DIR, num_tasks, num_inters), 'w') as s_file:
            for tr_ratio, sched_ratio in zip(c_to_tr_ratio_set, feasible):
                s_file.write('{:.5f},{:.5f}\n'.format(tr_ratio, sched_ratio))
            
            s_file.close()
        
        print('Done\t tasks: {: <10} inters: {: <10}'.format(num_tasks, num_inters))
        return c_to_tr_ratio_set, feasible
    

def parametric_workload_run_mp(num_tasksets = 1000, c_to_tr_points = 100, verbose = False):
    
    #####################################################
    num_tasks_l = [4, 8, 16, 24]
    num_inters_l = [1, 2, 4, 8]
    #####################################################

    active = {}
    for num_tasks in num_tasks_l:
        for num_inters in num_inters_l:
            active[(num_tasks, num_inters)] = False
    #####################################################
    
    # 4 Tasks
    active[(4, 1)] = True
    active[(4, 2)] = True
    
    # 8 Tasks
    active[(8, 1)] = True
    active[(8, 2)] = True
    active[(8, 4)] = True
    
    # 16 Tasks
    active[(16, 1)] = True
    active[(16, 2)] = True
    active[(16, 4)] = True
    active[(16, 8)] = True
    
    # 24 Tasks
    active[(24, 2)] = True
    active[(24, 4)] = True
    active[(24, 8)] = True
    #########################################
    
    num_cores = os.cpu_count()
    #########################################
    
    # Make data output directory
    os.makedirs(OUT_DIR, exist_ok = True)
    
    results = {}
    # Launch an experiment for each configuration
    with fts.ProcessPoolExecutor(max_workers = num_cores) as executor:
        for num_tasks in num_tasks_l:
            for num_inters in num_inters_l:
                if active[(num_tasks, num_inters)]:
                    future = executor.submit(test_bin_fixed_config,
                                            num_tasks, num_inters,
                                            num_tasksets, c_to_tr_points, verbose)
                    results[(num_tasks, num_inters)] = future

    for num_tasks in num_tasks_l:
        # For each number of tasks, generate a different plot to show the
        # feasibility ratio while varying the number of Interconnects
        plt.figure()
        plt.title('{} Tasks'.format(num_tasks))
        for num_inters in num_inters_l:
            if active[(num_tasks, num_inters)]:
                future = results[(num_tasks, num_inters)]
                c_to_tr_ratio_set, feasible = future.result()
                plt.plot(c_to_tr_ratio_set, feasible, label = '{} Int.'.format(num_inters))
             
        plt.legend()
        plt.savefig('{}/plot_t_{}.pdf'.format(OUT_DIR, num_tasks))
        
    print('All DONE')


###################################################################################################

if __name__ == '__main__':
    np.random.seed(100)
    parametric_workload_run_mp(num_tasksets = 50000, c_to_tr_points = 100, verbose = False)

