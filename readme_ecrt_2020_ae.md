ECRTS - Artifact Evaluation
============

This tutorial explains how to reproduce the experiments presented in the paper:

> *Francesco Restuccia, Marco Pagani, Alessandro Biondi, Mauro Marinoni, and Giorgio Buttazzo, "Modeling and Analysis of Bus Contention for Hardware Accelerators in FPGA SoCs",  In Proceedings of the 32nd Euromicro Conference on Real-Time Systems (ECRTS 2020), July 7-10, 2020.*

In particular, it describes how to replicate the experimental study that has been carried out in Section 5.4 to evaluate the proposed analysis with synthetic workloads.

Before commencing with the setup, please consider that running the proposed experiments may take a substantial amount of time. For instance, an entire run may take up to 12 hours on a modern desktop multicore PC. However, the code has been designed to take advantage of modern multicore platforms. Hence, please consider using a dedicated machine having eight or more processing cores for replicating the experiments in a reasonable amount of time.

### Environment setup
The schedulability analyses presented in the paper have been implemented with Python 3. Although Python code is platform-independent, the instructions provided in this tutorial describe how to replicate the experiments in a GNU/Linux environment.

In order to run the experiments, the following packages are required:

```console
Pyhton 3.7
NumPy
Matplotlib
NetworkX
```

On Ubuntu derived distributions, these packages can be installed via the following apt command:
```console
sudo apt-get install python3-numpy python3-matplotlib python3-networkx
```

On Fedora and derived distributions, these packages can be installed via the following dnf command:
```console
sudo dnf install python3-numpy python3-matplotlib python3-networkx
```

### Running the experiments
Once the environment has been prepared, a zip archive containing the source code of the simulator can be downloaded at this [link](https://retis.sssup.it/~m.pagani/aes/axi_sim_ae.zip). Alternatively, the same process can be conveniently performed within a shell using the following commands:

```console
wget https://retis.sssup.it/~m.pagani/aes/axi_sim_ae.zip
unzip axi_sim_ae.zip
cd axi_sim_ae/sim
```

Then, the experiment can be started by running the following command:

```console
python3 experiments.py
```

During the execution, the experiment produces the following output on the shell, notifying the completion by writing `ALL DONE` on the console.

```console
Start	 tasks: 4          inters: 1         
Start	 tasks: 4          inters: 2         
Start	 tasks: 8          inters: 1         
Start	 tasks: 8          inters: 2         
Start	 tasks: 8          inters: 4         
Start	 tasks: 16         inters: 1         
Start	 tasks: 16         inters: 2         
Start	 tasks: 16         inters: 4         
Start	 tasks: 16         inters: 8         
Start	 tasks: 24         inters: 2         
Start	 tasks: 24         inters: 4         
Start	 tasks: 24         inters: 8         
Done	 tasks: 4          inters: 1         
Done	 tasks: 4          inters: 2         
Done	 tasks: 8          inters: 1         
Done	 tasks: 8          inters: 2         
Done	 tasks: 8          inters: 4         
Done	 tasks: 16         inters: 1         
Done	 tasks: 16         inters: 2         
Done	 tasks: 16         inters: 4         
Done	 tasks: 16         inters: 8         
Done	 tasks: 24         inters: 2         
Done	 tasks: 24         inters: 4         
Done	 tasks: 24         inters: 8         
All DONE
```

Once the experiment is completed, the output results can be found in the `data` subdirectory. 

```console
cd data
```

For each configuration, the experiment produces a separate `csv` data files named according to the following name scheme `sched_t_N_i_M.csv` where `N` is the number of tasks and `M` the number of interconnects.

These files have been used for generating the graphs presented in Figure 8. In order to make the evaluation more convenient, the experiment also produces a graphical preview of the results using the `Matplotlib` Python package. These preview graphs are available in the `data` directory as a set of `plot_t_N.pdf` files where `N` is the number of tasks. As in Figure 8, each preview plot shows the schedulability ratio for the given number of tasks while varying the bus load considering a different number of interconnects. Please note that the color palette used for the preview plots is slightly different from the one used in Figure 8.


