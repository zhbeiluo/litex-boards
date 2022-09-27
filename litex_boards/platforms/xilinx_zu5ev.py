#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2022 Ilia Sergachev <ilia@sergachev.ch>
# SPDX-License-Identifier: BSD-2-Clause

from typing import IO
from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform, VivadoProgrammer


# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("clk100", 0,
        Subsignal("p", Pins("AC12"), IOStandard("LVDS_25")),
        Subsignal("n", Pins("AD11"), IOStandard("LVDS_25"))
    ),
    ("uart_sel", 0, Pins("AD14"), IOStandard("LVCMOS18")),

]

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "clk100"
    default_clk_period = 1e9 / 100e6

    def __init__(self, toolchain="vivado"):
        XilinxPlatform.__init__(self, "xczu5ev-sfvc784-2-i", _io, toolchain=toolchain)
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]", ]
        self.default_clk_freq = 1e9 / self.default_clk_period

    def create_programmer(self):
        return VivadoProgrammer()

    def do_finalize(self, fragment, *args, **kwargs):
        XilinxPlatform.do_finalize(self, fragment, *args, **kwargs)
        self.add_period_constraint(self.lookup_request(self.default_clk_name, loose=True), self.default_clk_period)
