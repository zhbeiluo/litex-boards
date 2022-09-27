#!/usr/bin/env python3

#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2022 Icenowy Zheng <icenowy@aosc.io>
# Copyright (c) 2022 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.cores.clock.gowin_gw2a import GW2APLL
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.builder import *
from litex.soc.cores.led import LedChaser, WS2812
from litex.soc.cores.gpio import GPIOIn
from litex.soc.cores.video import *

from liteeth.phy.rmii import LiteEthPHYRMII

from litex_boards.platforms import sipeed_tang_primer_20k

from litedram.common import PHYPadsReducer
from litedram.modules import MT41J128M16
from litedram.phy import GW2DDRPHY

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq, with_video_pll=False):
        self.rst = Signal()
        self.clock_domains.cd_sys     = ClockDomain()
        self.clock_domains.cd_por     = ClockDomain()
        self.clock_domains.cd_init    = ClockDomain()
        self.clock_domains.cd_sys2x   = ClockDomain()
        self.clock_domains.cd_sys2x_i = ClockDomain()

        # # #

        self.stop  = Signal()
        self.reset = Signal()

        # Clk
        clk27 = platform.request("clk27")

        # Power on reset (the onboard POR is not aware of reprogramming)
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(clk27)
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        self.submodules.pll = pll = GW2APLL(devicename=platform.devicename, device=platform.device)
        self.comb += pll.reset.eq(~por_done)
        pll.register_clkin(clk27, 27e6)
        pll.create_clkout(self.cd_sys2x_i, 2*sys_clk_freq)
        self.specials += [
            Instance("DHCEN",
                i_CLKIN  = self.cd_sys2x_i.clk,
                i_CE     = self.stop,
                o_CLKOUT = self.cd_sys2x.clk),
            Instance("CLKDIV",
                p_DIV_MODE = "2",
                i_CALIB    = 0,
                i_HCLKIN   = self.cd_sys2x.clk,
                i_RESETN   = ~self.reset,
                o_CLKOUT   = self.cd_sys.clk),
            AsyncResetSynchronizer(self.cd_sys, ~pll.locked | self.reset),
        ]

        # Init clock domain
        self.comb += self.cd_init.clk.eq(clk27)
        self.comb += self.cd_init.rst.eq(pll.reset)

        # Video PLL
        if with_video_pll:
            self.submodules.video_pll = video_pll = GW2APLL(devicename=platform.devicename, device=platform.device)
            video_pll.register_clkin(clk27, 27e6)
            self.clock_domains.cd_hdmi   = ClockDomain()
            self.clock_domains.cd_hdmi5x = ClockDomain()
            video_pll.create_clkout(self.cd_hdmi5x, 125e6, margin=1e-3)
            self.specials += Instance("CLKDIV",
                p_DIV_MODE = "5",
                i_RESETN   = 1, # Disable reset signal.
                i_CALIB    = 0, # No calibration.
                i_HCLKIN   = self.cd_hdmi5x.clk,
                o_CLKOUT   = self.cd_hdmi.clk
            )

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(48e6),
        with_spi_flash      = False,
        with_led_chaser     = True,
        with_rgb_led        = False,
        with_buttons        = True,
        with_video_terminal = False,
        with_ethernet       = False,
        with_etherbone      = False,
        eth_ip              = "192.168.1.50",
        eth_dynamic_ip      = False,
        dock                = "standard",
        **kwargs):

        assert dock in ["standard", "lite"]

        platform = sipeed_tang_primer_20k.Platform(dock, toolchain="gowin")

        if dock == "lite":
            with_led_chaser = False # No leds on core board nor on dock lite.

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq, with_video_pll=with_video_terminal)

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq, ident="LiteX SoC on Tang Primer 20K", **kwargs)

        # DDR3 SDRAM -------------------------------------------------------------------------------
        # FIXME: WIP.
        if not self.integrated_main_ram_size:
            self.submodules.ddrphy = GW2DDRPHY(
                pads         = PHYPadsReducer(platform.request("ddram"), [0, 1]),
                sys_clk_freq = sys_clk_freq
            )
            self.ddrphy.settings.rtt_nom = "disabled"
            self.comb += self.crg.stop.eq(self.ddrphy.init.stop)
            self.comb += self.crg.reset.eq(self.ddrphy.init.reset)
            self.add_sdram("sdram",
                phy           = self.ddrphy,
                module        = MT41J128M16(sys_clk_freq, "1:2"),
                l2_cache_size = 0
            )
            # ./sipeed_tang_primer_20k.py --cpu-variant=lite --uart-name=crossover+uartbone --csr-csv=csr.csv --build --load
            # litex_server --uart --uart-port=/dev/ttyUSB2
            # litex_term crossover
            # litescope_cli
            if kwargs["uart_name"] == "crossover+uartbone":
                from litescope import LiteScopeAnalyzer
                analyzer_signals = [
                    self.ddrphy.dfi.p0,
                    self.ddrphy.dfi.p0.wrdata_en,
                    self.ddrphy.dfi.p1.rddata_en,
                ]
                self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
                depth        = 128,
                clock_domain = "sys",
                samplerate   = sys_clk_freq,
                csr_csv      = "analyzer.csv"
                )

        # SPI Flash --------------------------------------------------------------------------------
        if with_spi_flash:
            from litespi.modules import W25Q32JV as SpiFlashModule
            from litespi.opcodes import SpiNorFlashOpCodes as Codes
            self.add_spi_flash(mode="1x", module=SpiFlashModule(Codes.READ_1_1_1))

        # Ethernet / Etherbone ---------------------------------------------------------------------
        if with_ethernet or with_etherbone:
            # FIXME: Un-tested.
            from liteeth.phy.rmii import LiteEthPHYRMII
            self.submodules.ethphy = LiteEthPHYRMII(
                clock_pads = self.platform.request("eth_clocks"),
                pads       = self.platform.request("eth"),
                refclk_cd  = None
            )
            if with_ethernet:
                self.add_ethernet(phy=self.ethphy, dynamic_ip=eth_dynamic_ip, with_timing_constraints=False)
            if with_etherbone:
                self.add_etherbone(phy=self.ethphy, ip_address=eth_ip, with_timing_constraints=False)

        # Video ------------------------------------------------------------------------------------
        if with_video_terminal:
            # FIXME: Un-tested.
            hdmi_pads = platform.request("hdmi")
            self.comb += hdmi_pads.hdp.eq(1)
            self.submodules.videophy = VideoHDMIPHY(hdmi_pads, clock_domain="hdmi", pn_swap=["r", "g", "b"])
            self.add_video_colorbars(phy=self.videophy, timings="640x480@60Hz", clock_domain="hdmi")
            #self.add_video_terminal(phy=self.videophy, timings="640x480@75Hz", clock_domain="hdmi")

        # Leds -------------------------------------------------------------------------------------
        if with_led_chaser:
            self.submodules.leds = LedChaser(
                pads         = platform.request_all("led"),
                sys_clk_freq = sys_clk_freq
            )

        # RGB Led ----------------------------------------------------------------------------------
        if with_rgb_led:
            self.submodules.rgb_led = WS2812(
                pad          = platform.request("rgb_led"),
                nleds        = 1,
                sys_clk_freq = sys_clk_freq
            )
            self.bus.add_slave(name="rgb_led", slave=self.rgb_led.bus, region=SoCRegion(
                origin = 0x2000_0000,
                size   = 4,
            ))

        # Buttons ----------------------------------------------------------------------------------
        if with_buttons:
            self.submodules.buttons = GPIOIn(pads=~platform.request_all("btn_n"))


# Build --------------------------------------------------------------------------------------------

def main():
    from litex.soc.integration.soc import LiteXSoCArgumentParser
    parser = LiteXSoCArgumentParser(description="LiteX SoC on Tang Primer 20K")
    target_group = parser.add_argument_group(title="Target options")
    target_group.add_argument("--dock",         default="standard",    help="Dock version (standard (default) or lite.")
    target_group.add_argument("--build",        action="store_true",   help="Build bitstream.")
    target_group.add_argument("--load",         action="store_true",   help="Load bitstream.")
    target_group.add_argument("--flash",        action="store_true",   help="Flash Bitstream.")
    target_group.add_argument("--sys-clk-freq", default=48e6,          help="System clock frequency.")
    sdopts = target_group.add_mutually_exclusive_group()
    sdopts.add_argument("--with-spi-sdcard",      action="store_true", help="Enable SPI-mode SDCard support.")
    sdopts.add_argument("--with-sdcard",          action="store_true", help="Enable SDCard support.")
    target_group.add_argument("--with-spi-flash", action="store_true", help="Enable SPI Flash (MMAPed).")
    target_group.add_argument("--with-video-terminal", action="store_true", help="Enable Video Terminal (HDMI).")
    ethopts = target_group.add_mutually_exclusive_group()
    ethopts.add_argument("--with-ethernet",  action="store_true",    help="Add Ethernet.")
    ethopts.add_argument("--with-etherbone", action="store_true",    help="Add EtherBone.")
    target_group.add_argument("--eth-ip",          default="192.168.1.50", help="Etherbone IP address.")
    target_group.add_argument("--eth-dynamic-ip",  action="store_true",    help="Enable dynamic Ethernet IP addresses setting.")
    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()

    soc = BaseSoC(
        sys_clk_freq        = int(float(args.sys_clk_freq)),
        with_spi_flash      = args.with_spi_flash,
        with_video_terminal = args.with_video_terminal,
        with_ethernet       = args.with_ethernet,
        with_etherbone      = args.with_etherbone,
        eth_ip              = args.eth_ip,
        eth_dynamic_ip      = args.eth_dynamic_ip,
        dock                = args.dock,
        **soc_core_argdict(args)
    )
    if args.with_spi_sdcard:
        soc.add_spi_sdcard()
    if args.with_sdcard:
        soc.add_sdcard()

    builder = Builder(soc, **builder_argdict(args))
    if args.build:
        builder.build()

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))

    if args.flash:
        prog = soc.platform.create_programmer()
        prog.flash(0, builder.get_bitstream_filename(mode="flash", ext=".fs"), external=True)

if __name__ == "__main__":
    main()
