#!/usr/bin/env python3
#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2021 Antmicro <www.antmicro.com>
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse
import math
import json

from migen import *

from litex_boards.platforms import datacenter_ddr4_test_board
from litex.build.xilinx.vivado import vivado_build_args, vivado_build_argdict

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.builder import *
from litex.soc.cores.led import LedChaser
from litex.soc.cores.bitbang import I2CMaster

from litedram.modules import MTA18ASF2G72PZ
from litedram.phy.s7ddrphy import A7DDRPHY
from litedram.init import get_sdram_phy_py_header
from litedram.core.controller import ControllerSettings
from litedram.common import PhySettings, GeomSettings, TimingSettings

from liteeth.phy import LiteEthS7PHYRGMII
from litex.soc.cores.hyperbus import HyperRAM

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq, iodelay_clk_freq):
        self.clock_domains.cd_sys       = ClockDomain()
        self.clock_domains.cd_sys2x     = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys4x     = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys4x_dqs = ClockDomain(reset_less=True)
        self.clock_domains.cd_idelay    = ClockDomain()

        # # #

        self.submodules.pll = pll = S7PLL(speedgrade=-1)
        pll.register_clkin(platform.request("clk100"), 100e6)
        pll.create_clkout(self.cd_sys,       sys_clk_freq)
        pll.create_clkout(self.cd_sys2x,     2 * sys_clk_freq)
        pll.create_clkout(self.cd_sys4x,     4 * sys_clk_freq)
        pll.create_clkout(self.cd_sys4x_dqs, 4 * sys_clk_freq, phase=90)
        pll.create_clkout(self.cd_idelay,    iodelay_clk_freq)

        self.submodules.idelayctrl = S7IDELAYCTRL(self.cd_idelay)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, *, sys_clk_freq=int(100e6), iodelay_clk_freq=200e6,
            with_ethernet=False, with_etherbone=False, eth_ip="192.168.1.50", eth_dynamic_ip=False,
            with_hyperram=False, with_sdcard=False, with_jtagbone=True, with_uartbone=False,
            with_led_chaser=True, eth_reset_time, **kwargs):
        platform = datacenter_ddr4_test_board.Platform()

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq,
            ident = "LiteX SoC on data center test board",
            **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq, iodelay_clk_freq=iodelay_clk_freq)

        # DDR4 SDRAM RDIMM -------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            self.submodules.ddrphy = A7DDRPHY(platform.request("ddr4"),
                memtype         = "DDR4",
                iodelay_clk_freq = iodelay_clk_freq,
                sys_clk_freq     = sys_clk_freq,
                is_rdimm         = True,
            )
            self.add_sdram("sdram",
                phy                     = self.ddrphy,
                module                  = MTA18ASF2G72PZ(sys_clk_freq, "1:4"),
                l2_cache_size           = kwargs.get("l2_size", 8192),
                l2_cache_min_data_width = 256,
                size                    = 0x40000000,
            )

        # HyperRAM ---------------------------------------------------------------------------------
        if with_hyperram:
            self.submodules.hyperram = HyperRAM(platform.request("hyperram"))
            self.bus.add_slave("hyperram", slave=self.hyperram.bus, region=SoCRegion(origin=0x20000000, size=8*1024*1024))

        # SD Card ----------------------------------------------------------------------------------
        if with_sdcard:
            self.add_sdcard()

        # Ethernet / Etherbone ---------------------------------------------------------------------
        if with_ethernet or with_etherbone:
            # Traces between PHY and FPGA introduce ignorable delays of ~0.165ns +/- 0.015ns.
            # PHY chip does not introduce delays on TX (FPGA->PHY), however it includes 1.2ns
            # delay for RX CLK so we only need 0.8ns to match the desired 2ns.
            self.submodules.ethphy = LiteEthS7PHYRGMII(
                clock_pads = self.platform.request("eth_clocks"),
                pads       = self.platform.request("eth"),
                rx_delay   = 0.8e-9,
                hw_reset_cycles = math.ceil(float(eth_reset_time) * self.sys_clk_freq)
            )
            if with_ethernet:
                self.add_ethernet(phy=self.ethphy, dynamic_ip=eth_dynamic_ip)
            if with_etherbone:
                self.add_etherbone(phy=self.ethphy, ip_address=eth_ip)

        # UartBone ---------------------------------------------------------------------------------
        if with_uartbone:
            self.add_uartbone("serial", baudrate=1e6)

        # Leds -------------------------------------------------------------------------------------
        if with_led_chaser:
            self.submodules.leds = LedChaser(
                pads         = platform.request_all("user_led"),
                sys_clk_freq = sys_clk_freq)

        # System I2C (behing multiplexer) ----------------------------------------------------------
        i2c_pads = platform.request('i2c')
        self.submodules.i2c = I2CMaster(i2c_pads)

    def generate_sdram_phy_py_header(self, output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        f = open(output_file, "w")
        f.write(get_sdram_phy_py_header(
            self.sdram.controller.settings.phy,
            self.sdram.controller.settings.timing))
        f.close()


# Build --------------------------------------------------------------------------------------------

class LiteDRAMSettingsEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (ControllerSettings, GeomSettings, PhySettings, TimingSettings)):
            ignored = ['self', 'refresh_cls']
            return {k: v for k, v in vars(o).items() if k not in ignored}
        elif isinstance(o, Signal) and isinstance(o.reset, Constant):
            return o.reset
        elif isinstance(o, Constant):
            return o.value
        print('o', end=' = '); __import__('pprint').pprint(o)
        return super().default(o)

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on LPDDR4 Test Board")
    target = parser.add_argument_group(title="Target options")
    target.add_argument("--build",            action="store_true",    help="Build bitstream.")
    target.add_argument("--load",             action="store_true",    help="Load bitstream.")
    target.add_argument("--flash",            action="store_true",    help="Flash bitstream.")
    target.add_argument("--sys-clk-freq",     default=100e6,           help="System clock frequency.")
    target.add_argument("--iodelay-clk-freq", default=200e6,          help="IODELAYCTRL frequency.")
    ethopts = target.add_mutually_exclusive_group()
    ethopts.add_argument("--with-ethernet",   action="store_true",    help="Add Ethernet.")
    ethopts.add_argument("--with-etherbone",  action="store_true",    help="Add EtherBone.")
    target.add_argument("--eth-ip",           default="192.168.1.50", help="Ethernet/Etherbone IP address.")
    target.add_argument("--eth-dynamic-ip",   action="store_true",    help="Enable dynamic Ethernet IP addresses setting.")
    target.add_argument("--eth-reset-time",   default="10e-3",        help="Duration of Ethernet PHY reset")
    target.add_argument("--with-hyperram",    action="store_true",    help="Add HyperRAM.")
    target.add_argument("--with-sdcard",      action="store_true",    help="Add SDCard.")
    target.add_argument("--with-jtagbone",    action="store_true",    help="Add JTAGBone.")
    target.add_argument("--with-uartbone",    action="store_true",    help="Add UartBone on 2nd serial.")
    builder_args(parser)
    soc_core_args(parser)
    vivado_build_args(parser)
    args = parser.parse_args()

    assert not (args.with_etherbone and args.eth_dynamic_ip)

    soc = BaseSoC(
        sys_clk_freq      = int(float(args.sys_clk_freq)),
        iodelay_clk_freq  = int(float(args.iodelay_clk_freq)),
        with_ethernet     = args.with_ethernet,
        with_etherbone    = args.with_etherbone,
        eth_ip            = args.eth_ip,
        eth_dynamic_ip    = args.eth_dynamic_ip,
        eth_reset_time    = args.eth_reset_time,
        with_hyperram     = args.with_hyperram,
        with_sdcard       = args.with_sdcard,
        with_jtagbone     = args.with_jtagbone,
        with_uartbone     = args.with_uartbone,
        **soc_core_argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    vns = builder.build(**vivado_build_argdict(args), run=args.build)

    builder.soc.generate_sdram_phy_py_header(os.path.join(builder.output_dir, "sdram_init.py"))

    # LiteDRAM settings (controller, phy, geom, timing)
    with open(os.path.join(builder.output_dir, 'litedram_settings.json'), 'w') as f:
        json.dump(builder.soc.sdram.controller.settings, f, cls=LiteDRAMSettingsEncoder, indent=4)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

    if args.flash:
        prog = soc.platform.create_programmer()
        prog.flash(0, os.path.join(builder.gateware_dir, soc.build_name + ".bin"))

if __name__ == "__main__":
    main()
