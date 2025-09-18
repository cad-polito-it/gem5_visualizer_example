# Gem5 Pipeline Visualizer example

## Usage

### 1. Requirements
- Ubuntu 22.04
- A working [RISC-V toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain), preferably version 2023.10.18
- Our custom version of [gem5](https://github.com/cad-polito-it/gem5)
- The [pipeline visualizer](https://github.com/cad-polito-it/gem5_pipeline_visualizer)

### 2. Write your RISC-V program
Use the editor of your choice (nano, Visual Studio Code, gedit, ...) to write
a RISC-V assembly file and save it. An `example.s` is provided in this repo

### 3. Compile it
Compile your example:
```
<path_to_your_riscv_toolchain>/riscv32-unknown-elf-gcc -march=rv32imf -mabi=ilp32 -mno-relax -nostartfiles <your_assembly_file> -o <output_executable_name>
```

If you are using the virtual machine or a LABINF PC, the `riscv_compile` script can be used:
```
riscv_compile <your_assembly_file>
```
It will produce an executable with the same name as the assembly file.

### 4. Run gem5
In order to run the simulation, you will need a Python configuration file. Use the `gem5_config.py` provided with this repository (remember to copy the 
`common` folder along with `gem5_config.py` if you are copying it in a different folder).
```
<path_to_gem5>/build/RISCV/gem5.opt
  --debug-flags=MinorGUI
  gem5_config.py
  --cpu-type MinorCPU
  --caches
  --l1d_size 8388608
  --l1i_size 8388608
  --cacheline_size 512
  --cpu-clock 1MHz
  --sys-clock 10GHz
  -c <output_executable_name> > <log_file_name>
```
Provide the executable file produced in the previous step and specify a log file. `gem5_config.py` must be used to specify pipeline parameters like
functional unit latencies.

On the virtual machine and on LABINF PCs, the command `gem5_run` provides a shortcut to start the simulation. It takes as arguments the Python file
containing the gem5 system configuration, the executable you want to run and the name of the log file where you want gem5's output to be. For example:
```
gem5_run gem5_config.py example example.log
```

### 5. Open the log file with the visualizer
Open the pipeline visualizer, click on `File -> Open` and select the log file generated in the
previous step.
On the virtual machine, the visualizer is available as a command `gem5_pipeline_visualizer`.
