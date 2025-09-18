# Copyright (c) 2012-2013 ARM Limited
# All rights reserved.
#
# The license below extends only to copyright in the software and shall
# not be construed as granting a license to any other intellectual
# property including but not limited to intellectual property relating
# to a hardware implementation of the functionality of the software
# licensed hereunder.  You may use the software subject to the license
# terms below provided that you ensure that this notice is replicated
# unmodified and in its entirety in all distributions of the software,
# modified or unmodified, in source code or in binary form.
#
# Copyright (c) 2006-2008 The Regents of The University of Michigan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Simple test script
#
# "m5 test.py"

import argparse
import sys
import os

import m5
from m5.defines import buildEnv
from m5.objects import *
from m5.params import NULL
from m5.util import addToPath, fatal, warn
from gem5.isas import ISA
from gem5.runtime import get_runtime_isa

addToPath("../")

from common import Options
from common import Simulation
from common import CacheConfig
from common import CpuConfig
from common import ObjectList
from common import MemConfig
from common.FileSystemConfig import config_filesystem
from common.Caches import *
from common.cpu2000 import *

# Functional units latencies. In order:
# - Integer ALU and Memory access address calculation
# - Integer Multiplication
# - Integer Division
# - Float ALU
# - Float Multiplication
# - Float Division

# The latency specifies the number of cycles it takes for the
# functional unit to execute an instruction after it is issued.
# The INTEGER_ALU_LATENCY controls also the latency of the memory
# address calculation
INTEGER_ALU_LATENCY = 1
INTEGER_MUL_LATENCY = 1
INTEGER_DIV_LATENCY = 1
FLOAT_ALU_LATENCY = 3
FLOAT_MUL_LATENCY = 5
FLOAT_DIV_LATENCY = 5

# The issue latency is the number of cycles until another instruction can be issued 
# to the functional unit after an instruction has already been issued.
# The INTEGER_ALU_ISSUE_LATENCY controls also the issue latency of the memory
# address calculation
INTEGER_ALU_ISSUE_LATENCY = 0
INTEGER_MUL_ISSUE_LATENCY = 0
INTEGER_DIV_ISSUE_LATENCY = 0
FLOAT_ALU_ISSUE_LATENCY = 0
FLOAT_MUL_ISSUE_LATENCY = 0
FLOAT_DIV_ISSUE_LATENCY = 5



def get_process(args):
    """Interprets provided args and returns a list of processes"""

    inputs = None
    outputs = None
    errouts = None
    pargs = None

    workload = args.cmd
    if args.input != "":
        inputs = args.input
    if args.output != "":
        outputs = args.output
    if args.errout != "":
        errouts = args.errout
    if args.options != "":
        pargs = args.options

    process = Process(pid=100)
    process.executable = workload
    process.cwd = os.getcwd()
    process.gid = os.getgid()

    if args.env:
        with open(args.env, "r") as f:
            process.env = [line.rstrip() for line in f]

    if pargs is not None:
        process.cmd = [workload] + pargs.split()
    else:
        process.cmd = [workload]
    if inputs is not None:
        process.input = inputs
    if outputs is not None:
        process.output = outputs
    if errouts is not None:
        process.errout = errouts

    return process


parser = argparse.ArgumentParser()
Options.addCommonOptions(parser)
Options.addSEOptions(parser)

args = parser.parse_args()

if args.cmd:
    process = get_process(args)
else:
    print("No workload specified. Exiting!\n", file=sys.stderr)
    sys.exit(1)

(CPUClass, test_mem_mode, FutureClass) = Simulation.setCPUClass(args)
CPUClass.numThreads = 1

mp0_path = process.executable
system = System(
    cpu=[CPUClass(cpu_id=0)],
    mem_mode=test_mem_mode,
    mem_ranges=[AddrRange(args.mem_size)],
    cache_line_size=args.cacheline_size,
)

system.multi_thread = False

# Create a top-level voltage domain
system.voltage_domain = VoltageDomain(voltage=args.sys_voltage)

# Create a source clock for the system and set the clock period
system.clk_domain = SrcClockDomain(
    clock=args.sys_clock, voltage_domain=system.voltage_domain
)

# Create a CPU voltage domain
system.cpu_voltage_domain = VoltageDomain()

# Create a separate clock domain for the CPUs
system.cpu_clk_domain = SrcClockDomain(
    clock=args.cpu_clock, voltage_domain=system.cpu_voltage_domain
)

# All cpus belong to a common cpu_clk_domain, therefore running at a common
# frequency.

system.cpu[0].clk_domain = system.cpu_clk_domain

def minorMakeOpClassSet(op_classes):
    """Make a MinorOpClassSet from a list of OpClass enum value strings"""

    def boxOpClass(op_class):
        return MinorOpClass(opClass=op_class)

    return MinorOpClassSet(opClasses=[boxOpClass(o) for o in op_classes])


system.cpu[0].executeInputWidth = 1
system.cpu[0].executeInputBufferSize = 1
system.cpu[0].decodeInputBufferSize = 1
system.cpu[0].executeIssueLimit = 2
system.cpu[0].executeMemoryIssueLimit = 1
system.cpu[0].decodeToExecuteForwardDelay = 1
system.cpu[0].enableIdling = False
system.cpu[0].fetch1LineWidth = 512

#############################################################################
# MODIFIABLE PART #
#############################################################################

# Functional units indices
# 0: Integer ALU, Memory access address calculation
# 1: Integer Multiplication
# 2: Integer Division
# 3: Float ALU
# 4: Float Multiplication
# 5: Float Division

# The parameter opLat is the latency of the functional unit, i.e., the number of cycles it takes for the
# functional unit to execute an instruction after it is issued.
system.cpu[0].executeFuncUnits.funcUnits[0].opLat = INTEGER_ALU_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[1].opLat = INTEGER_MUL_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[2].opLat = INTEGER_DIV_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[3].opLat = FLOAT_ALU_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[4].opLat = FLOAT_MUL_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[5].opLat = FLOAT_DIV_LATENCY
# The parameter issueLat controls the issue latency of the functional unit, i.e., the number of cycles
# until another instruction can be issued to the functional unit after an instruction has already been issued.
system.cpu[0].executeFuncUnits.funcUnits[0].issueLat = INTEGER_ALU_ISSUE_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[1].issueLat = INTEGER_MUL_ISSUE_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[2].issueLat = INTEGER_DIV_ISSUE_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[3].issueLat = FLOAT_ALU_ISSUE_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[4].issueLat = FLOAT_MUL_ISSUE_LATENCY
system.cpu[0].executeFuncUnits.funcUnits[5].issueLat = FLOAT_DIV_ISSUE_LATENCY


# The parameter timings is a list of MinorFUTiming objects, each of which specifies the latency of the
# functional unit for a specific operation class. The parameter srcRegsRelativeLats specifies the
# relative latency of the source registers for each operation class. The parameter extraAssumedLat should
# not be touched.
system.cpu[0].executeFuncUnits.funcUnits[0].timings = [
    MinorFUTiming(
        description="Int",
        opClasses=minorMakeOpClassSet(["IntAlu"]),
        srcRegsRelativeLats=[0, 0],
    ),
    MinorFUTiming(
        description="Mem",
        opClasses=minorMakeOpClassSet(
            ["MemRead", "MemWrite", "FloatMemRead", "FloatMemWrite"]
        ),
        srcRegsRelativeLats=[1, 0],
        extraAssumedLat=0,
    ),
]

system.cpu[0].executeFuncUnits.funcUnits[4].timings = [
    MinorFUTiming(
        description="FloatMult",
        opClasses=minorMakeOpClassSet(["FloatMult"]),
        srcRegsRelativeLats=[0, 0],
        extraCommitLat=0,
    ),
]
# The parameter cantForwardFromFUIndices specifies the indices of the functional units from which the
# functional unit cannot forward results.
system.cpu[0].executeFuncUnits.funcUnits[5].cantForwardFromFUIndices = [3, 4]
system.cpu[0].executeFuncUnits.funcUnits[5].timings[0].srcRegsRelativeLats = [
    0
]
system.cpu[0].executeFuncUnits.funcUnits[5].timings[0].extraAssumedLat = 1

system.cpu[0].executeFuncUnits.funcUnits[4].cantForwardFromFUIndices = [3, 5]
system.cpu[0].executeFuncUnits.funcUnits[4].timings[0].srcRegsRelativeLats = [
    0
]

system.cpu[0].executeFuncUnits.funcUnits[3].cantForwardFromFUIndices = [4, 5]
system.cpu[0].executeFuncUnits.funcUnits[3].timings[0].srcRegsRelativeLats = [
    0
]

##################################################################
# END OF MODIFIABLE PART #
##################################################################

system.cpu[0].workload = process

system.cpu[0].createThreads()

MemClass = Simulation.setMemClass(args)

system.membus = SystemXBar()
system.membus.clk_domain = system.clk_domain
system.membus.forward_latency = 1
system.membus.frontend_latency = 1
system.membus.header_latency = 1
system.membus.response_latency = 1
system.system_port = system.membus.cpu_side_ports

CacheConfig.config_cache(args, system)

MemConfig.config_mem(args, system)
config_filesystem(system, args)

for memctrl in system.mem_ctrls:
    memctrl.clk_domain = system.clk_domain
    memctrl.dram.clk_domain = system.clk_domain
    memctrl.static_frontend_latency = "0.001ns"
    memctrl.static_backend_latency = "0.001ns"
    memctrl.command_window = "0.001ns"
    #        if isinstance(memctrl.dram, DRAMInterface):
    memctrl.dram.tREFI = "1000000000000ns"
    memctrl.dram.tBURST = "0.001ns"
    memctrl.dram.tRCD = "0.001ns"
    memctrl.dram.tRCD_WR = "0.001ns"
    memctrl.dram.tCL = "0.001ns"
    memctrl.dram.tCWL = "0.001ns"
    memctrl.dram.tPPD = "0.001ns"
    memctrl.dram.tRAS = "0.001ns"
    memctrl.dram.tWR = "0.001ns"
    memctrl.dram.tRFC = "0.001ns"
    memctrl.dram.tRP = "0.001ns"
    memctrl.dram.tRRD = "0.001ns"
    memctrl.dram.tRTP = "0.001ns"
    memctrl.dram.tWR = "0.001ns"
    memctrl.dram.tWTR_L = "0.001ns"
    memctrl.dram.tXAW = "0.001ns"
    memctrl.dram.tXP = "0.001ns"
    memctrl.dram.tXPDLL = "0.001ns"
    memctrl.dram.tXS = "0.001ns"
    memctrl.dram.tXSDLL = "0.001ns"
    memctrl.dram.tCK = "0.001ns"

system.workload = SEWorkload.init_compatible(mp0_path)

if args.wait_gdb:
    system.workload.wait_for_remote_gdb = True

root = Root(full_system=False, system=system)

system.cpu[0].icache_port.data_latency = "0.001ns"
system.cpu[0].icache_port.tag_latency = "0.001ns"
system.cpu[0].icache_port.response_latency = "0.001ns"
system.cpu[0].dcache_port.data_latency = "0.001ns"
system.cpu[0].dcache_port.tag_latency = "0.001ns"
system.cpu[0].dcache_port.response_latency = "0.001ns"
system.cpu[0].icache_port.clk_domain = system.clk_domain
system.cpu[0].dcache_port.clk_domain = system.clk_domain
system.cpu[0].icache_port.size = 8388608
system.cpu[0].dcache_port.size = 8388608
system.cpu[0].dcache_port.peer.clk_domain = system.clk_domain
system.cpu[0].icache_port.peer.clk_domain = system.clk_domain

Simulation.run(args, root, system, FutureClass)
