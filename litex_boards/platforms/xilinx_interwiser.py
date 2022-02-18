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
    ("user_led",  0, Pins("H10"), IOStandard("LVCMOS33")),
    ("user_led",  1, Pins("H9"),  IOStandard("LVCMOS33")),
    ("user_led",  2, Pins("G10"), IOStandard("LVCMOS33")),
    ("user_led",  3, Pins("F10"), IOStandard("LVCMOS33")),
    ("user_led",  4, Pins("H11"), IOStandard("LVCMOS33")),
    ("user_led",  5, Pins("G11"), IOStandard("LVCMOS33")),
    ("user_led",  6, Pins("G12"), IOStandard("LVCMOS33")),
    ("user_led",  7, Pins("F12"), IOStandard("LVCMOS33")),

    # swtiches 
    ("user_sw",  0, Pins("E11"), IOStandard("LVCMOS33")),
    ("user_sw",  1, Pins("E10"), IOStandard("LVCMOS33")),
        
    # buttons
    ("user_btn", 0, Pins("E12"), IOStandard("LVCMOS33")),
    ("user_btn", 1, Pins("D12"), IOStandard("LVCMOS33")),
    ("user_btn", 2, Pins("B12"), IOStandard("LVCMOS33")),
    ("user_btn", 3, Pins("A12"), IOStandard("LVCMOS33")),
    ("user_btn", 4, Pins("B11"), IOStandard("LVCMOS33")),

    # HDMI
    # Clk
    ("clk100",   0, Pins("F9"),  IOStandard("LVCMOS18")),

]

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "clk100"
    default_clk_period = 1e9/100e6

    def __init__(self, toolchain="vivado"):
        XilinxPlatform.__init__(self, "xczu2eg-sfva625-1-e", _io, toolchain=toolchain)
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]", ]
        self.default_clk_freq = 1e9 / self.default_clk_period

    def create_programmer(self):
        return VivadoProgrammer()

    def do_finalize(self, fragment, *args, **kwargs):
        XilinxPlatform.do_finalize(self, fragment, *args, **kwargs)
        self.add_period_constraint(self.lookup_request("clk100", loose=True), 1e9/100e6)
