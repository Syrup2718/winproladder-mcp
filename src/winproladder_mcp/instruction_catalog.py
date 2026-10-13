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
