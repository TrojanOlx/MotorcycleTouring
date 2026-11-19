"""Read-only OBD-II RPM example using simulated, headers-off ELM replies."""

import re
from typing import Callable


class OBDResponseError(ValueError):
    """The adapter did not return one complete, usable response."""


class UnsupportedPID(OBDResponseError):
    """The ECU did not advertise support for engine RPM."""


def payload(raw: str, command: str, prefix: str, size: int) -> bytes:
    response = raw.strip()
    if not response.endswith(">"):
        raise OBDResponseError(f"{command}: missing adapter prompt")

    frames = []
    for line in response[:-1].splitlines():
        compact = "".join(line.upper().split())
        if compact in ("", command, "SEARCHING..."):
            continue
        if (
            len(compact) != size * 2
            or not compact.startswith(prefix)
            or not re.fullmatch(r"[0-9A-F]+", compact)
        ):
            raise OBDResponseError(f"{command}: unexpected reply: {line.strip()}")
        frames.append(bytes.fromhex(compact))

    if len(frames) != 1:
        raise OBDResponseError(f"{command}: expected one reply, got {len(frames)}")
    return frames[0][2:]


def read_rpm(exchange: Callable[[str], str]) -> float:
    """Ask for supported PIDs first; query RPM only when advertised.

    exchange owns command framing and the I/O timeout. It must return the
    entire response through '>' or raise a transport error. This function
    never caches or substitutes a reading.
    """
    supported = payload(exchange("0100"), "0100", "4100", 6)
    if not (int.from_bytes(supported, "big") & (1 << (32 - 0x0C))):
        raise UnsupportedPID("ECU did not advertise PID 0C (engine RPM)")

    data = payload(exchange("010C"), "010C", "410C", 4)
    return int.from_bytes(data, "big") / 4


if __name__ == "__main__":
    simulated = {"0100": "41 00 00 10 00 00\r>", "010C": "41 0C 1A F8\r>"}

    def demo_exchange(command: str) -> str:
        reply = simulated[command]
        print(f"{command} -> {reply!r}")
        return reply

    print(f"SIMULATED: {read_rpm(demo_exchange):g} RPM")
