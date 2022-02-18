#!/usr/bin/env python3

#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2022 Ilia Sergachev <ilia@sergachev.ch>
# SPDX-License-Identifier: BSD-2-Clause

# Build/Use:
# The current support is sufficient to run LiteX BIOS on Cortex-A53 core #0:
# ./xilinx_kv260.py --build --load
# LiteX BIOS can then be executed on hardware using JTAG with the following xsct script from:
# https://github.com/sergachev/litex-template/tree/kv260
# make -f Makefile.kv260 load will build everything and run xsct in the end.
#
# Relies on https://github.com/lucaceresoli/zynqmp-pmufw-builder to create a generic PMU firmware;
# first build will take a while because it includes a cross-toolchain.

import argparse
from xml.dom import minidom

from migen import *

from litex_boards.platforms import xilinx_interwiser
from litex.build.xilinx.vivado import vivado_build_args, vivado_build_argdict
from litex.build.tools import write_to_file

from litex.soc.interconnect import axi
from litex.soc.interconnect import wishbone

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.builder import *

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq, use_ps7_clk=False):
        self.rst = Signal()
        self.clock_domains.cd_sys = ClockDomain()

        # # #

        if use_ps7_clk:
            self.comb += ClockSignal("sys").eq(ClockSignal("ps"))
            self.comb += ResetSignal("sys").eq(ResetSignal("ps") | self.rst)
        else:
            self.submodules.pll = pll = S7PLL(speedgrade=-1)
            self.comb += pll.reset.eq(self.rst)
            pll.register_clkin(platform.request(platform.default_clk_name), platform.default_clk_freq)
            pll.create_clkout(self.cd_sys, sys_clk_freq)
            # Ignore sys_clk to pll.clkin path created by SoC's rst.
            platform.add_false_path_constraints(self.cd_sys.clk, pll.clkin)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    mem_map = {"csr": 0xA000_0000}  # default GP0 address on ZynqMP

    def __init__(self, sys_clk_freq, **kwargs):
        platform = xilinx_interwiser.Platform()

        if kwargs.get("cpu_type", None) == "zynqmp":
            kwargs['integrated_sram_size'] = 0

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq,
            ident = "LiteX SoC on InterWiser",
            **kwargs)

        # ZynqMP Integration -----------------------------------------------------------------------
        if kwargs.get("cpu_type", None) == "zynqmp":
            self.add_configs_xml("interwiser.xml")

            # Connect Zynq AXI master to the SoC
            wb_gp0 = wishbone.Interface()
            self.submodules += axi.AXI2Wishbone(
                axi          = self.cpu.add_axi_gp_master(),
                wishbone     = wb_gp0,
                base_address = self.mem_map["csr"])
            self.add_wb_master(wb_gp0)
            self.bus.add_region("sram", SoCRegion(
                origin=self.cpu.mem_map["sram"],
                size=2 * 1024 * 1024 * 1024)  # DDR
            )
            self.bus.add_region("rom", SoCRegion(
                origin=self.cpu.mem_map["rom"],
                size=512 * 1024 * 1024 // 8,
                linker=True)
            )
            self.constants['CONFIG_CLOCK_FREQUENCY'] = 1333333008

            use_ps7_clk = True
        else:
            use_ps7_clk = False

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq, use_ps7_clk)
    
    def add_configs_xml(self, preset=None):
        if preset == None:
            return
        if preset.split(".")[-1] == "xml":
            print(f"Read configs from {preset}")
            cfgs = self._read_from_xml(preset)
            self.cpu.config.update(cfgs)
    
    def _read_from_xml(self, preset):
        dom = minidom.parse(preset)
        cfgs = {}
        root = dom.documentElement
        params = root.getElementsByTagName('user_parameter')
        for i in range(len(params)):
            pn = params[i].getAttribute("name")           
            pv = params[i].getAttribute("value")
            pp = pn.split('.')[-1]
            cfgs[pp] = pv
        
        return cfgs

    def finalize(self, *args, **kwargs):
        super(BaseSoC, self).finalize(*args, **kwargs)
        if self.cpu_type != "zynqmp":
            return

        libxil_path = os.path.join(self.builder.software_dir, 'libxil')
        os.makedirs(os.path.realpath(libxil_path), exist_ok=True)
        lib = os.path.join(libxil_path, 'embeddedsw')
        if not os.path.exists(lib):
            os.system("git clone --depth 1 https://github.com/Xilinx/embeddedsw {}".format(lib))

        os.makedirs(os.path.realpath(self.builder.include_dir), exist_ok=True)

        for header in [
            'XilinxProcessorIPLib/drivers/uartps/src/xuartps_hw.h',
            'lib/bsp/standalone/src/common/xil_types.h',
            'lib/bsp/standalone/src/common/xil_assert.h',
            'lib/bsp/standalone/src/common/xil_io.h',
            'lib/bsp/standalone/src/common/xil_printf.h',
            'lib/bsp/standalone/src/common/xstatus.h',
            'lib/bsp/standalone/src/common/xdebug.h',
            'lib/bsp/standalone/src/arm/ARMv8/64bit/xpseudo_asm.h',
            'lib/bsp/standalone/src/arm/ARMv8/64bit/xreg_cortexa53.h',
            'lib/bsp/standalone/src/arm/ARMv8/64bit/xil_cache.h',
            'lib/bsp/standalone/src/arm/ARMv8/64bit/xil_errata.h',
            'lib/bsp/standalone/src/arm/ARMv8/64bit/platform/ZynqMP/xparameters_ps.h',
            'lib/bsp/standalone/src/arm/common/xil_exception.h',
            'lib/bsp/standalone/src/arm/common/gcc/xpseudo_asm_gcc.h',
        ]:
            shutil.copy(os.path.join(lib, header), self.builder.include_dir)

        write_to_file(os.path.join(self.builder.include_dir, 'bspconfig.h'), """
#ifndef BSPCONFIG_H
#define BSPCONFIG_H

#define EL3 1
#define EL1_NONSECURE 0

#endif
""")
        write_to_file(os.path.join(self.builder.include_dir, 'xparameters.h'), '''
#ifndef XPARAMETERS_H
#define XPARAMETERS_H

#include "xparameters_ps.h"

#define STDIN_BASEADDRESS 0xFF010000
#define STDOUT_BASEADDRESS 0xFF010000
#define XPAR_PSU_DDR_0_S_AXI_BASEADDR 0x00000000
#define XPAR_PSU_DDR_0_S_AXI_HIGHADDR 0x7FFFFFFF
#define XPAR_PSU_DDR_1_S_AXI_BASEADDR 0x800000000
#define XPAR_PSU_DDR_1_S_AXI_HIGHADDR 0x87FFFFFFF
#define XPAR_CPU_CORTEXA53_0_TIMESTAMP_CLK_FREQ 99999001

#endif
''')


# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Interwiser")
    parser.add_argument("--build",        action="store_true", help="Build bitstream.")
    parser.add_argument("--load",         action="store_true", help="Load bitstream.")
    parser.add_argument("--sys-clk-freq", default=100e6,       help="System clock frequency.")
    parser.add_argument("--preset", default="interwiser.xml", help="preset file")
    builder_args(parser)
    soc_core_args(parser)
    vivado_build_args(parser)
    parser.set_defaults(cpu_type="zynqmp")
    parser.set_defaults(no_uart=True)
    args = parser.parse_args()

    soc = BaseSoC(
        sys_clk_freq=int(float(args.sys_clk_freq)),
        **soc_core_argdict(args)
    )
    builder = Builder(soc, **builder_argdict(args))
    if args.cpu_type == "zynqmp":
        soc.builder = builder
        builder.add_software_package('libxil')
        builder.add_software_library('libxil')
    builder.build(**vivado_build_argdict(args), run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))


if __name__ == "__main__":
    main()
