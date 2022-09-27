#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2021 Sergiu Mosanu <sm7ed@virginia.edu>
#
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import Pins, Subsignal, IOStandard, Misc
from litex.build.xilinx import XilinxPlatform, VivadoProgrammer

# IOs -----------------------------------------------------------------------------------------------

_io = [
    # 125MHz Clk / Rst from SGMII
    ("sysclk", 0, 
        Subsignal("p", Pins("BH6"), IOStandard("DIFF_SSTL12")),
        Subsignal("n", Pins("BJ6"), IOStandard("DIFF_SSTL12"))
    ),
    
    ("cpu_reset", 0, Pins("BF2"), IOStandard("LVCMOS18")),

    # Leds
    # ("gpio_led", 0, Pins("C32"), IOStandard("LVCMOS18")),
    # ("gpio_led", 1, Pins("D32"), IOStandard("LVCMOS18")),
    # ("gpio_led", 2, Pins("D31"), IOStandard("LVCMOS18")),

    # DDR4 SDRAM
    #("ddram_reset_gate", 0, Pins(""), IOStandard("LVCMOS12")),???
    ("ddram", 0,
        Subsignal("a", Pins(
            "BK45 BL45 BL43 BN44 BP46 BL46 BH46 BJ43",
            "BN46 BN45 BM42 BM45 BH44 BL42"), # we_n=BE43 cas_n=BL46 ras_n=BH44
            IOStandard("SSTL12_DCI")),
        Subsignal("we_n", Pins("BH41"), IOStandard("SSTL12_DCI")), # A14
        Subsignal("cas_n", Pins("BK43"), IOStandard("SSTL12_DCI")), # A15
        Subsignal("ras_n", Pins("BJ41"), IOStandard("SSTL12_DCI")), # A16
        Subsignal("act_n", Pins("BP44"), IOStandard("SSTL12_DCI")),
        Subsignal("ba", Pins("BK41 BG43"), IOStandard("SSTL12_DCI")),
        Subsignal("bg", Pins("BK46 BJ44"), IOStandard("SSTL12_DCI")),
        Subsignal("cke", Pins("BM47"), IOStandard("SSTL12_DCI")),
        Subsignal("clk_n", Pins("BJ42"), IOStandard("DIFF_SSTL12_DCI")),
        Subsignal("clk_p", Pins("BH42"), IOStandard("DIFF_SSTL12_DCI")),
        Subsignal("cs_n", Pins("BG42"), IOStandard("SSTL12_DCI")),
        Subsignal("dq", Pins(
            "BE49 BE51 BF50 BF52 BE50 BD51 BG50 BF51",
            "BE54 BG52 BG54 BK54 BE53 BG53 BK53 BH52",
            "BH51 BJ51 BH50 BJ49 BK50 BK51 BH49 BJ48",
            "BL53 BL52 BN50 BM48 BL51 BM52 BN51 BN49",
            "BF35 BH35 BJ33 BG35 BF36 BH34 BJ34 BG34",
            "BN34 BL33 BL31 BK31 BP34 BM33 BL32 BK33",
            "BP32 BN31 BP28 BL30 BP31 BN32 BP29 BM30",
            "BH31 BH29 BF31 BF32 BH30 BJ31 BG32 BF33"),
            # ECC excluded 8 pins
            # "BE44 BE43 BF42 BF43 BF45 BF46 BD42 BC42"
            IOStandard("POD12_DCI"),
            Misc("PRE_EMPHASIS=RDRV_240"),
            Misc("EQUALIZATION=EQ_LEVEL2")),
        Subsignal("dqs_n", Pins(
            "BF48 BJ54 BJ47 BM50 BK35 BM35 BN30 BK30"), #"BE46"
            IOStandard("DIFF_POD12"), # DIFF_POD12_DCI
            Misc("PRE_EMPHASIS=RDRV_240"),
            Misc("EQUALIZATION=EQ_LEVEL2")),
        Subsignal("dqs_p", Pins(
            "BF47 BH54 BH47 BM49 BK34 BL35 BN29 BJ29"), #"BE45"
            IOStandard("DIFF_POD12"), # DIFF_POD12_DCI
            Misc("PRE_EMPHASIS=RDRV_240"),
            Misc("EQUALIZATION=EQ_LEVEL2")),
        Subsignal("odt", Pins("BF41"), IOStandard("SSTL12_DCI")),
        Subsignal("reset_n", Pins("BL47"), IOStandard("LVCMOS12")),
        Misc("SLEW=FAST")
    ),
    ("serial", 0,
        Subsignal("rx", Pins("E14"), IOStandard("LVCMOS18")),
        Subsignal("tx", Pins("F15"), IOStandard("LVCMOS18")),
    ),

    ("uart_sel", 0, Pins("BG3"), IOStandard("LVCMOS18")),

    # PCIe (hardware tests in progress)
    ("pcie_x16", 0,
        Subsignal("rst_n", Pins("BF5"), IOStandard("LVCMOS18")),
        Subsignal("clk_n", Pins("AR14")),
        Subsignal("clk_p", Pins("AR15")),
        Subsignal("rx_n", Pins(
            "AL1 AM3 AN5 AN1 AP3 AR1 AT3 AU1",
            "AV3 AW5 AW1 AY3 BA5 BA1 BB3 BC1")),
        Subsignal("rx_p", Pins(
            "AL2 AM4 AN6 AN2 AP4 AR2 AT4 AU2",
            "AV4 AW6 AW2 AY4 BA6 BA2 BB4 BC2")),
        Subsignal("tx_n", Pins(
            "AL10 AM8 AN10 AP8 AR10 AR6 AT8 AU10",
            "AU6 AV8 AW10 AY8 BA10 BB8 BC10 BC6")),
        Subsignal("tx_p", Pins(
            "AL11 AM9 AN11 AP9 AR11 AR7 AT9 AU11",
            "AU7 AV9 AW11 AY9 BA11 BB9 BC11 BC7")),
    ),

    # PCIe (hardware tests in progress)
    ("pcie_x4", 0,
        Subsignal("rst_n", Pins("BF5"), IOStandard("LVCMOS18")),
        Subsignal("clk_n", Pins("AR14")),
        Subsignal("clk_p", Pins("AR15")),
        Subsignal("rx_n",  Pins("AL1 AM3 AN5 AN1")),
        Subsignal("rx_p",  Pins("AL2 AM4 AN6 AN2")),
        Subsignal("tx_n",  Pins("AL10 AM8 AN10 AP8")),
        Subsignal("tx_p",  Pins("AL11 AM9 AN11 AP9")),
    ),

    # QSFP Clock (not tested on hardware)
    # ("qsfp_156mhz_clock", 0,
    #     Subsignal("n", Pins("T43")),
    #     Subsignal("p", Pins("T42")),
    # ),
    # ("qsfp_156mhz_clock", 1,
    #     Subsignal("n", Pins("P43")),
    #     Subsignal("p", Pins("P42")),
    # ),

    # QSFP28 (not tested on hardware)
    # This board has QSFPDD, need addtional codes
    # ("qsfp28", 0,
    #     Subsignal("clk_n", Pins("R41")),
    #     Subsignal("clk_p", Pins("R40")),
    #     #Subsignal("fs0", Pins(""), IOStandard("LVCMOS18")), # not found in u280 pins
    #     #Subsignal("fs1", Pins(""), IOStandard("LVCMOS18")), # not found in u280 pins
    #     Subsignal("intl", Pins("B32")),
    #     Subsignal("lpmode", Pins("C29")),
    #     Subsignal("modprsl", Pins("A33")),
    #     Subsignal("modskll", Pins("A31")),
    #     #Subsignal("refclk_reset", Pins(""), IOStandard("LVCMOS12")), # not found in u280 pins
    #     Subsignal("resetl", Pins("B30")),
    #     Subsignal("rxn", Pins("L54 K52 J54 H52")),
    #     Subsignal("rxp", Pins("L53 K51 J53 H51")),
    #     Subsignal("txn", Pins("L49 L45 K47 J49")),
    #     Subsignal("txp", Pins("L48 L44 K46 J48")),
    # ),
    # ("qsfp28", 1,
    #     Subsignal("clk_n", Pins("M43")),
    #     Subsignal("clk_p", Pins("M42")),
    #     #Subsignal("fs0", Pins(""), IOStandard("LVCMOS18")), # not found in u280 pins
    #     #Subsignal("fs1", Pins(""), IOStandard("LVCMOS18")), # not found in u280 pins
    #     Subsignal("intl", Pins("E29")),
    #     Subsignal("lpmode", Pins("F29")),
    #     Subsignal("modprsl", Pins("F33")),
    #     Subsignal("modskll", Pins("D30")),
    #     #Subsignal("refclk_reset", Pins(""), IOStandard("LVCMOS12")), # not found in u280 pins
    #     Subsignal("resetl", Pins("E33")),
    #     Subsignal("rxn", Pins("G54 F52 E54 D52")),
    #     Subsignal("rxp", Pins("G53 F51 E53 D51")),
    #     Subsignal("txn", Pins("G49 E49 C49 A50")),
    #     Subsignal("txp", Pins("G48 E48 C48 A49")),
    # ),
]

# Connectors ---------------------------------------------------------------------------------------

_connectors = []

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "sysclk"
    default_clk_period = 1e9/125e6

    def __init__(self, toolchain="vivado"):
        XilinxPlatform.__init__(self, "xcvu37p-fsvh2892-2-e", _io, _connectors, toolchain=toolchain)

    def create_programmer(self):
        return VivadoProgrammer()

    def do_finalize(self, fragment):
        XilinxPlatform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request("sysclk", 0, loose=True), 1e9/100e6)
        # self.add_period_constraint(self.lookup_request("sysclk", 1, loose=True), 1e9/100e6)

        # For passively cooled boards, overheating is a significant risk if airflow isn't sufficient
        self.add_platform_command("set_property BITSTREAM.CONFIG.OVERTEMPSHUTDOWN ENABLE [current_design]")
        # Reduce programming time
        self.add_platform_command("set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]")
        # DDR4 memory channel C0 Internal Vref
        self.add_platform_command("set_property INTERNAL_VREF 0.84 [get_iobanks 64]")
        self.add_platform_command("set_property INTERNAL_VREF 0.84 [get_iobanks 65]")
        self.add_platform_command("set_property INTERNAL_VREF 0.84 [get_iobanks 66]")

        # Other suggested configurations
        self.add_platform_command("set_property CONFIG_VOLTAGE 1.8 [current_design]")
        self.add_platform_command("set_property BITSTREAM.CONFIG.CONFIGFALLBACK Enable [current_design]")
        self.add_platform_command("set_property CONFIG_MODE SPIx4 [current_design]")
        self.add_platform_command("set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]")
        self.add_platform_command("set_property BITSTREAM.CONFIG.CONFIGRATE 85.0 [current_design]")
        self.add_platform_command("set_property BITSTREAM.CONFIG.EXTMASTERCCLK_EN disable [current_design]")
        self.add_platform_command("set_property BITSTREAM.CONFIG.SPI_FALL_EDGE YES [current_design]")
        self.add_platform_command("set_property BITSTREAM.CONFIG.UNUSEDPIN Pullup [current_design]")
        self.add_platform_command("set_property BITSTREAM.CONFIG.SPI_32BIT_ADDR Yes [current_design]")

        # For HBM2 IP in Vivado 2019.2 (https://www.xilinx.com/support/answers/72607.html)
        # self.add_platform_command("connect_debug_port dbg_hub/clk [get_nets apb_clk]")