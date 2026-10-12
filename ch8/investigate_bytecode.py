## Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
"""Bounded bytecode triage helper used by the stablecoin case lab.

solc turns Solidity into EVM bytecode (opcodes + immediate data). This module
does not compile; it only walks already-compiled runtime bytes looking for a
common function-dispatcher shape compilers emit for external calls.
"""


def decode(code):
    """Decode a byte string into (pc, opcode, push_argument) triples.

    Opcodes 0x60..0x7f are PUSH1..PUSH32: the next 1..32 bytes are the immediate
    value (for example PUSH4 selector). All other opcodes take no immediate.
    """
    ops, pc = [], 0
    while pc < len(code):
        op = code[pc]
        width = op - 0x5f if 0x60 <= op <= 0x7f else 0
        arg = code[pc + 1:pc + 1 + width]
        if len(arg) != width:
            raise ValueError(f"Truncated PUSH at byte {pc}")
        ops.append((pc, op, arg))
        pc += 1 + width
    return ops


def candidates(code):
    """Find likely function-selector branches in runtime bytecode.

    Typical Solidity dispatcher fragment for one external function:
      PUSH4 <selector>   (0x63 + 4 bytes)   compare calldataload selector
      EQ                 (0x14)
      PUSH1/2 <dest>     (0x60..0x62)        jump target
      JUMPI              (0x57)              jump if equal
      ...
      JUMPDEST           (0x5b) at <dest>    start of that function's code

    A match here is only a byte pattern. It does not prove the function runs,
    is reachable in practice, or implements the source require() checks.
    """
    ops, found = decode(code), []
    for a, b, c, d in zip(ops, ops[1:], ops[2:], ops[3:]):
        if a[1] == 0x63 and b[1] == 0x14 and 0x60 <= c[1] <= 0x62:
            dest = int.from_bytes(c[2], "big")
            if d[1] == 0x57 and any(p == dest and o == 0x5b for p, o, _ in ops):
                found.append({"offset": a[0], "selector": "0x" + a[2].hex(),
                              "jumpdest": dest})
    return found
