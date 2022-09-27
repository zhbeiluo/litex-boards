#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2022 Congwu Zhang <zhangcongwu@ict.ac.cn>
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform, VivadoProgrammer


# IOs ----------------------------------------------------------------------------------------------

# currently, ios are used to test functionality

_io = [
    # leds
    ("user_led",  0, Pins("H9"), IOStandard("LVCMOS33")),
    ("user_led",  1, Pins("J9"), IOStandard("LVCMOS33")),
    ("user_led",  2, Pins("H8"), IOStandard("LVCMOS33")),
    ("user_led",  3, Pins("J8"), IOStandard("LVCMOS33")),
    # HDMI
    # Clk
    ("clk125",   0, 
        Subsignal("p", Pins("AU21"), IOStandard("DIFF_SSTL12")),
        Subsignal("n", Pins("AV21"), IOStandard("DIFF_SSTL12")),
    ),
    ("cpu_reset", 0, Pins("AB27"), IOStandard("LVCMOS33")),
    # I2C

    # ddram
    ("ddram", 0,
        Subsignal("a",       Pins(
            "BA20 AW19 AY19 AT21 AN21 AP21 BA18 AP20",
            "BB20 AW20 AW21 AY18 BB19 AT22"),
            IOStandard("SSTL12_DCI")),
        Subsignal("ba",      Pins("BA21 AY20"), IOStandard("SSTL12_DCI")),
        Subsignal("bg",      Pins("AR19 AV19"), IOStandard("SSTL12_DCI")),
        Subsignal("ras_n",   Pins("AR22"), IOStandard("SSTL12_DCI")), # A16
        Subsignal("cas_n",   Pins("AV22"), IOStandard("SSTL12_DCI")), # A15
        Subsignal("we_n",    Pins("BA22"), IOStandard("SSTL12_DCI")), # A14
        Subsignal("cs_n",    Pins("AL20"), IOStandard("SSTL12_DCI")), # also AL17 AN17 AN16 for larger SODIMMs
        Subsignal("act_n",   Pins("AU20"), IOStandard("SSTL12_DCI")),
        #Subsignal("alert_n", Pins("AB15"), IOStandard("SSTL12_DCI")),
        #Subsignal("par",     Pins("AD16"), IOStandard("SSTL12_DCI")),
        Subsignal("dm",      Pins("AW24 AR23 AM19 AU24 AY17 AY12 AV17 AJ18"),
            IOStandard("POD12_DCI")),
        Subsignal("dq",      Pins(
                "BB24 BB25 AY25 BA25 AY27 AY28 BA28 BB28",
                "AP24 AP25 AM24 AN24 AK23 AL23 AJ24 AK24",
                "AM21 AM20 AL22 AL21 AJ21 AJ20 AJ22 AK22",
                "AV26 AW26 AV27 AW27 AU25 AU26 AT25 AT26",
                "BA16 BB16 AW17 AW16 AY15 AY14 BA13 BB13",
                "BA11 BB11 BA10 BB10 AW15 AW14 AU14 AV14",
                "AT15 AU15 AU18 AV18 AR17 AT17 AT16 AU16",
                "AL18 AM18 AN18 AN17 AL16 AM16 AN16 AP16"),
            IOStandard("POD12_DCI"),
            Misc("PRE_EMPHASIS=RDRV_240"),
            Misc("EQUALIZATION=EQ_LEVEL2")),
        Subsignal("dqs_p",   Pins("BA26 AM23 AK20 AU28 BA15 AU13 AR18 AJ17"),
            IOStandard("DIFF_POD12_DCI"),
            Misc("PRE_EMPHASIS=RDRV_240"),
            Misc("EQUALIZATION=EQ_LEVEL2")),
        Subsignal("dqs_n",   Pins("BB26 AN23 AK19 AV28 BB15 AV13 AT18 AK17"),
            IOStandard("DIFF_POD12_DCI"),
            Misc("PRE_EMPHASIS=RDRV_240"),
            Misc("EQUALIZATION=EQ_LEVEL2")),
        Subsignal("clk_p",   Pins("BA23"), IOStandard("DIFF_SSTL12_DCI")), # also AJ16 for larger SODIMMs
        Subsignal("clk_n",   Pins("BB23"), IOStandard("DIFF_SSTL12_DCI")), # also AJ15 for larger SODIMMs
        Subsignal("cke",     Pins("BB18"), IOStandard("SSTL12_DCI")), # also AM15 for larger SODIMMs
        Subsignal("odt",     Pins("AP22"), IOStandard("SSTL12_DCI")), # also AM16 for larger SODIMMs
        Subsignal("reset_n", Pins("AR20"), IOStandard("LVCMOS12")),
        Misc("SLEW=FAST"),
    ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "clk125"
    default_clk_period = 1e9/100e6

    def __init__(self, toolchain="vivado"):
        XilinxPlatform.__init__(self, "xczu19eg-ffvc1760-2-e", _io, toolchain=toolchain)
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]", ]
        self.default_clk_freq = 1e9 / self.default_clk_period

    def create_programmer(self):
        return VivadoProgrammer()

    def do_finalize(self, fragment, *args, **kwargs):
        XilinxPlatform.do_finalize(self, fragment, *args, **kwargs)
        self.add_period_constraint(self.lookup_request("clk125", loose=True), 1e9/100e6)
        self.add_platform_command("set_property INTERNAL_VREF 0.84 [get_iobanks 64]")
        self.add_platform_command("set_property INTERNAL_VREF 0.84 [get_iobanks 65]")
        self.add_platform_command("set_property INTERNAL_VREF 0.84 [get_iobanks 66]")
