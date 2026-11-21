"""CRC primitives used by the public LDR container codec."""


def crc16(data: bytes) -> int:
    """Return reflected CRC-16/IBM with initial register ``0xFFFF``."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc
