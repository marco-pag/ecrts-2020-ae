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

import copy
import numpy as np
from abc import ABC

import matplotlib.pyplot as plt
import networkx as nx

###################################################################################################

class Topology(ABC):
    '''
    Topology describing:
    1) number of Interconnects + positions via adjacency matrix (descending edges)
    2) number of HW-tasks + the position using an array
    '''
    def __init__(self, workload):
        self._workload = workload
        self._tasks_adj = np.full(workload.num_tasks, -1)
        self._inters_adj = None
        self._inters_reach = None
        
    def _gen_inters_adj(self, num_inters):
        '''
        Generate adjacency matrix for the required number of Interconnects
        '''
        self._inters_adj = np.full((num_inters, num_inters), False, dtype = np.bool)
    
    def _gen_inters_reach(self):
        '''
        Generate transitive closure (reachability matrix) from the transposed
        adjacency matrix (ascending edges). This matrix is used to get the subtree
        of all Interconnects connected above a specific Interconnect
        '''
        self._inters_reach = copy.deepcopy(self._inters_adj.T)
        
        for k in range(self.num_inters):
            for i in range(self.num_inters):
                for j in range(self.num_inters):
                    self._inters_reach[i][j] = (self._inters_reach[i][j] or
                                    (self._inters_reach[i][k] and self._inters_reach[k][j]))
                    
    def get_tasks_by_inter(self, inter_idx):
        '''
        Get indexes of tasks directly connected to the Interconnect
        '''
        tasks_idxs = []
        for task_j, inter_i in enumerate(self._tasks_adj):
            if inter_i == inter_idx:
                tasks_idxs.append(task_j)
                
        return tasks_idxs
    
    def get_inters_below(self, inter_idx):
        '''
        Get indexes of Interconnects lying along the path to the root Interconnect
        '''
        inters_below = []
        while inter_idx != 0:
            for inter_j, is_below in enumerate(self._inters_adj[inter_idx]):               
                if is_below:
                    inters_below.append(inter_j)
                    inter_idx = inter_j
                    break
        
        return inters_below
    

    def get_inters_above(self, inter_idx):
        '''
        Get indexes of Interconnect lying along the path from the current
        interconnect to the root node
        '''
        assert self._inters_reach is not None
        inters_above = []
        for inter_j, is_up in enumerate(self._inters_reach[inter_idx]):
            if is_up:
                inters_above.append(inter_j)
        
        return inters_above
    

    def get_inters_above_dc(self, inter_idx):
        '''
        Get indexes of Interconnects directly connected to (above) the current Interconnect
        '''
        inter_above_dc = []
        for inter_j, link in enumerate(self._inters_adj.T[inter_idx]):
            if link:
                inter_above_dc.append(inter_j)
        
        return inter_above_dc
    
    def plot(self):
        graph = nx.from_numpy_matrix(self._inters_adj, create_using = nx.OrderedDiGraph)
        pos = nx.nx_agraph.graphviz_layout(graph, prog = "dot")
        nx.draw(graph, pos, with_labels = True)
        plt.show()
        
    def _sanity_check(self):
        '''
        Check if the topology is consistent
        '''
        if not np.allclose(self.inters_adj, np.tril(self.inters_adj)):
            raise RuntimeError('Interconnect adjacency matrix is not triangular!')
        
        for inter_row in self.inters_adj[1:]:
            if 1 not in inter_row:
                raise RuntimeError('Interconnect adjacency matrix unconnected!')

        for inter_i, _ in enumerate(self._inters_adj):
            if not self.get_tasks_by_inter(inter_i):
                raise RuntimeError('Interconnect without tasks!')

    def __str__(self):
        rout = 'Inter\tTasks\n'
        for inter_i, _ in enumerate(self._inters_adj):
            tasks = self.get_tasks_by_inter(inter_i)
            rout += str(inter_i) + '\t' + str(len(tasks)) + ': ' + str(tasks) + '\n'
        
        return rout
        
    @property
    def inters_adj(self):
        return self._inters_adj

    @property
    def num_inters(self):
        return self._inters_adj.shape[0]

    @property
    def tasks_adj(self):
        return self._tasks_adj  
   
    @property
    def num_tasks(self):
        return self._tasks_adj.shape[0]
    
    @property
    def inters_reach(self):
        return self._inters_reach
    
    @property
    def workload(self):
        return self._workload
        

###################################################################################################

'''
Topology that will distribute the ordered tasks set given as input evenly over a fixed
number of Interconnects
''' 
class BinaryEvenTopology(Topology):
    '''
    Generate a binary topology, i.e., binary tree of Interconnects with
    positions for HW-tasks
    '''
    def __init__(self, workload, num_inters, top_down = False):
        # At least two tasks per Interconnect
        assert workload.num_tasks >= num_inters * 2
        super().__init__(workload)
        self._gen_inters_adj(num_inters)
        self._top_down = top_down
        
        # Generate interconnect adjacency matrix
        # to create a binary tree of Interconnects
        parent_map = self._gen_inters_parent_map()
        for row_idx in range(1, num_inters):
            self._inters_adj[row_idx][parent_map[row_idx]] = True
            
        # Generate the corresponding reachability matrix
        self._gen_inters_reach()
        
        # Align workload
        self._workload.set_inters(num_inters)

        # Assign tasks to the Interconnects
        inters_seq = self._gen_inters_seq()
        #print(inters_seq)
        ti_ratio = np.ceil(self.num_tasks / num_inters).astype(int)
        ratio = 0
        inter_j = 0
        for task_i in range(self.num_tasks):
            self._tasks_adj[task_i] = inters_seq[inter_j]
            ratio += 1
            if ratio == ti_ratio:
                inter_j += 1
                ratio = 0
        
        self._sanity_check()
        
    def _gen_inters_parent_map(self):
        '''
        Generate a list whose elements are the 
        parent of each Interconnect
        '''
        seq = [0]
        level = 0
        last_inter = 0
        
        # each new level adds 2^level Interconnects
        while last_inter < self.num_inters:
            prev_inter = last_inter
            last_inter += 2 ** level
            level += 1
            sub_seq = list(reversed(range(prev_inter, last_inter)))
            seq.extend([i for i in sub_seq for _ in range(2)])
            
        return seq
    
    def _gen_inters_seq(self):
        '''
        Serialize Interconnects for tasks assignment
        '''
        if not self._top_down:
            seq = list(range(self.num_inters))
        else:
            seq = list(reversed(range(self.num_inters)))
        
        return seq


###################################################################################################

if __name__ == '__main__':
    pass
