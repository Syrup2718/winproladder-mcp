"""Sample payload evidence and opcode tables; not inferred from FUNC numbers.

Exact payloads are independent export oracles. Code maps include inferred variants;
GUI confirmation applies only to the specific files documented in docs/verification.md.
"""

BLOCK_CASES = (
    ("timer", 1, 100, 4, "4fe8fd80006403926ffcc104", "test.ldr N003"),
    ("timer", 2, 101, 0, "4fe8fd80006503946ffcc100", "test2.ldr N004"),
    ("timer", 1, 256, None, "4fe8fd8001000392", "test3.ldr N004"),
    ("timer", 2, 1000, None, "4fe8fd8003e80394", "test3.ldr N005"),
    ("timer", 3, 101, None, "4fe8fd8000650396", "test3.ldr N006"),
    ("counter", 1, 10, None, "4fe87fe8f940000a0592", "test3.ldr N007"),
    ("counter", 2, 16, None, "4fe87fe8f94000100594", "test3.ldr N008"),
    ("counter", 3, 17, None, "4fe87fe8f94000110596", "test3.ldr N009"),
)

LCNV_PAYLOADS = {
    0: "4fe8f57c0000010019a247d00001",
    2: "4fe8f57c0000010219ac47d20001",
    4: "4fe8f57c0000010419b647d40001",
    6: "4fe8f57c0000010619c047d60001",
    8: "4fe8f57c0000010819ca47d80001",
}

ARITHMETIC_PAYLOADS = {
    1: "4fe87fe8f6620100000540c8",
    2: "4fe87fe8f66440c8000140ca",
    3: "4fe87fe8f66640cc000240ce",
    4: "4fe87fe8f6680102001440d2",
}

EDGE_PAYLOADS = {
    "e0004000c101": "test4.ldr N005 / test7.ldr N000",
    "e0005001c103": "test4.ldr N006",
}

TEST8_PAYLOADS = {
    0: "4fe8f4960ac8",
    1: "4fe8f4984190",
    2: "e00050000100",
    3: "4febd102",
    4: "4feb1103",
    5: "4fe87fe8f46a0100010200006ffcc8746ffdc8756ffec876",
    6: "4fe8f4c6010840f0412c",
}

TEST9_PAYLOADS = {
    0: "4810fc880000",
    1: "4201910061009201e422c100",
    2: "5201fd8000640392",
    3: "fc890000",
    4: "4811fc880002",
    5: "4fe8f8f60874",
    6: "4fe8fcf70875",
    7: "400160026003f10000640b90",
}

TEST10_PAYLOADS = {
    0: "4fe8f4ca13a442580adc",
    1: "4fe8f4cc0b9a03920bd2",
    2: "4fe8f7da0064fff601006ffcc1006ffdc1016ffec102",
    3: "4fe8f5a6014d0bbc",
    4: "4fe8f4a408000820",
}

TEST11_PAYLOADS = {
    0: "f47f00150a0428def47f002208850902f47f002341bc03940101",
    1: "f47f00180eb00f78f47f002503f40c58f67f0026059400641103",
    2: "4fe8f47f000000000aca0aca",
    3: "4fe8f47f00010acc40ce",
    4: "4fe8f47f000200000ad0000044560ac6",
    5: "4fe8f47f000300000a1200000a140acc",
    6: "4fe8f47f000400000a0000000a020a04",
}

TEST12_PAYLOADS = {
    0: "4fe8f57f000540c0624e00005ffc3f70",
    1: "4fe8f57f000642cc666600001a966ffcc1006ffdc88b6ffec847",
    2: "4fe8f57f00073ffeb85200000a1e27fc6ffcc1016ffdc8136ffecbf7",
    3: "4fe8f47f0008000040f60b94",
}

TEST13_PAYLOADS = {
    0: "4fe8f47f00091b5c1b5e",
    1: "4fe8f47f000a3ffe5ffc",
    2: "4fe8f57f000b007b0bbc",
    3: "4fe8f47f000c0bbc",
    4: "4fe8f47f000d0a00",
    5: "4fe8f47f000e00000a2c0ac4",
    6: "4fe8f47f000f00003f7040f6",
}

TEST14_PAYLOADS = {
    0: "4fe8f47f001000001b5c515a6ffcc827",
    1: "4fe8f67f001100000f78400000000f8c",
    2: "4fe8f47f001200000aca0acc",
    3: "4fe8f47f001300000ace0ad2",
    4: "4fe8f47f0014000028003ffc",
    5: "4fe8f4e80000000a",
}

TEST15_PAYLOADS = {
    0: "4fe8f4ea000011d00810",
    1: "4fe8f6ec000a01051360087421706ffcc81a",
    2: "4fe8f6ee00010103023e138c6ffcc81b",
    3: "4fe8f6fc0388017800002172",
    4: "4fe8f6fa000a011400025ffe402c6ffcc81c",
}

ARITHMETIC_OPCODES = {
    "add": b"\xf6\x62",
    "sub": b"\xf6\x64",
    "mul": b"\xf6\x66",
    "div": b"\xf6\x68",
}

COMPARISON_FIRST_CODES = {"eq": 0x15, "gt": 0x16, "lt": 0x17, "ne": 0x18, "ge": 0x19, "le": 0x1A}

COMPARISON_CHAIN_CODES = {"eq": 0x21, "gt": 0x22, "lt": 0x23, "ne": 0x24, "ge": 0x25, "le": 0x26}

FLOAT_CODES = {
    "i_to_f": 0,
    "f_to_i": 1,
    "add": 2,
    "sub": 3,
    "mul": 4,
    "div": 5,
    "sqrt": 8,
    "sin": 9,
    "cos": 10,
    "tan": 11,
    "neg": 12,
    "abs": 13,
    "ln": 14,
    "exp": 15,
    "log": 16,
    "pow": 17,
    "asin": 18,
    "acos": 19,
    "atan": 20,
}

PERIPHERAL_CODES = {"tkey": "f4ea", "hkey": "f6ec", "dsw": "f6ee", "7sgdl": "f6fc", "muxi": "f6fa"}

PERIPHERAL_FIELDS = {
    "tkey": ["input", "destination", "key_start"],
    "hkey": ["input", "output", "destination", "key_start", "work"],
    "dsw": ["input", "output", "destination", "work"],
    "7sgdl": ["source", "output", "mode", "work"],
    "muxi": ["input", "output", "rows", "destination", "work"],
}


TEST16_PAYLOADS = {
    0: "4000f5d1005a",
    1: "48e4f4f2",
    2: "4fe8f4e50000",
    3: "4fe8f7e7010000000000",
    4: "481280077fe86fe8f51700640b900ba40bb80bcc6ffcc1006ffdc1016ffec102",
    5: "4fe87fe8f46c0a180a2a0a2c6ffcc815",
    6: "4fe8f5c000160a2c0a2e",
}


TEST17_PAYLOADS = {
    0: "4fe8f47427fa0a0057f46ffcc819",
    1: "4fe8f5c0000c0ac80af6",
    2: "4fe8f4e244b0432040dc",
    3: "4fe8f49c1a680a02",
    4: "4fe8f49a0a18",
    5: "4fe8f49e0ba2",
    6: "4fe8f4b90a04",
    7: "4fe8f77500080bb80bbc",
}


TEST18_PAYLOADS = {
    0: "4fe86811f55a000601000de8",
    1: "ef31000000000000",
    2: "4fe86812f55e011e0004286428740b8e402e",
    3: "4fe8f78ca7fe188000000000",
    4: "4fe8f4ba0a1400026ffcc100",
    5: "4fe86814f544000f0a18",
}


TEST19_PAYLOADS = {
    0: "4fe8f78d672e188000000000",
    1: "f5900002",
    2: "4fe86810fc410bfe058e6ffcc90a6ffdc90b",
    3: "f491",
    4: "4fe86005fc420bfa0bfc6ffcc1006ffdc118",
    5: "4fe86812fc4353b21db06ffcc8266ffdc811",
    6: "4fe86fe8f4540102010341ba41c00aca0ad00ad60adc0ae66ffdc826",
}


TEST20_PAYLOADS = {
    0: "4fe860016002f103280028026ffcc1006ffec811",
    1: "481068116002f81600000ac803b80aca40de40e06ffcc8746ffdc8756ffec10c",
    2: "4fe8f47e00004014400040020a1801800a1e6ffcc826",
    3: "4fe86fe87fe8f4060a000a1400070a64",
}


TEST21_PAYLOADS = {
    0: "40006fe87fe8f4080a0000010a120a146ffcc813",
    1: "48136fe87fe8f40a0a280a3c00090a50",
    2: "48146fe86005f40a0ac80adc00090af0",
    3: "4fe8f4ce0af60b200004",
    4: "4fe8f4c20ac80b900009",
}


TEST22_PAYLOADS = {
    0: "40007fe87fe8f50c00dc0a0000090a28",
    1: "4fe87fe86fe8f4100a000a1800090a14",
    2: "4fe8f5f800140b900003",
    3: "40026816f4460a280a000a0000090a16",
    4: "40036817f4580a000a000009",
    5: "40056fe8f4480a000a0400090a020a286ffcc815",
    6: "40076811f44a0ac80acc00090aca0a28",
    7: "4fe8f4d80a040b9000090105",
    8: "5feb",
}


TEST23_PAYLOADS = {
    0: "4007f4d22800281428280004",
    1: "4811f4d30a000a140a280007",
    2: "4815f4d440640a78408c0002",
    3: "58118002f4d50b9040640a14000f",
    4: "4008f4d60ac80adc0a02",
    5: "4811881288137fe86fe8f4120a140a2800010a64",
    6: "40016fe87fe8f40e0a0000040a28",
    7: "481660026fe87fe8f42a0b9000030bb8",
}


TEST24_PAYLOADS = {
    0: "400060007fe8f4020a040a040004",
    1: "4fe87fe8f44e0a180a180004",
    2: "40026813f44c0ac800090ac86ffcc816",
    3: "40066fe8f4560af40b360003",
    4: "40097fe8f75c00020ade",
    5: "4815f4ac0a160a28",
    6: "4810f4ae0a0a0821",
    7: "400bf8e4081a",
}


TEST25_PAYLOADS = {
    0: "4fe8f4b008000a00000b0007",
    1: "4fe8f4b20a2c0a2800020001",
    2: "4fe8f4b40a500a5400010001",
    3: "4fe8f4b60ade0bbc",
    4: "4fe8f4b80ac8",
    5: "4fe8f5bc00030a2c0820",
    6: "4fe8f6bd080000020ac8",
    7: "4fe8f47711ce19a02800",
}


TEST26_PAYLOADS = {
    0: "4fe8f47811ce11d015b8",
    1: "48136fe8f55000020a2c6ffcc100",
    2: "48116fe8f4520a020a2e6ffcc812",
    3: "4fe8f4a2402c28006ffcc102",
    4: "4fe8f5aa0009402c6ffcc817",
    5: "4fe8f47a0a780a8c",
    6: "4fe8f4790a500a5c",
    7: "4fe8f4a808000a0400030005",
}


TEST27_PAYLOADS = {
    0: "40016fe8f44d0a00082000090023",
    1: "4815f4e60a000ac80000",
    2: "48188819f4f000072042214422460000000000000b90",
    3: "4005f4dc0a280a64",
    4: "4000a0068811f4dd0000280028c8",
    5: "481af5bf000311d01298",
    6: "493cf5a90001136014f0",
    7: "400b600c600d600ef4280adc",
}


TEST28_PAYLOADS = {
    0: "400060016002f4140a000a02010001010a0a6ffcc8106ffdc811",
    1: "ef38000000000000",
    2: "4fe8f7f3100000640100",
    3: "4fe8f78ca7fe1c0000000000",
    4: "400af6fb000003e80a14",
    5: "4fe8f78da7fe1c0000000000",
    6: "400b6810600cfc0f0000018000010184018811d00001",
    7: "4fe8f4f0002929592955282024531043205413a4",
}


TEST29_PAYLOADS = {
    0: "4fe8f4f0003f183219341a361b381c3023482c56",
    1: "4fe8f4f0000f244a254c264e27552a572c5a40de",
    2: "ef30000000000000",
    3: "ef32000000000000",
    4: "ef33000000000000",
    5: "ef34000000000000",
    6: "ef35000000000000",
    7: "ef36000000000000",
}


TEST30_PAYLOADS = {
    0: "4fe8f4720ade",
    1: "40017fe86fe8f51e0a0000c8400000056ffcc81a",
    2: "48116813f35b0a0000004002001420a86ffcc8746ffdc8756ffec876",
    3: "481c681df75d0a04000040140014",
    4: "ef41000000000000",
    5: "ef42188000000000",
    6: "ef4a2cb100000000",
    7: "ef312bd800000000",
}
