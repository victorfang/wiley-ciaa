## Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
"""Compile two local Solidity inputs and separate ABI names from runtime bytecode."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from investigate_bytecode import candidates

HERE = Path(__file__).resolve().parent
# Matches pragma solidity >=0.7.0 <0.9.0 in the chapter .sol files.
SOLC_MIN, SOLC_MAX = (0, 7, 0), (0, 9, 0)


def relpath(path):
    """Path string relative to this package (or cwd) for report/console output."""
    path = Path(path).resolve()
    for root in (HERE, Path.cwd()):
        try:
            return str(path.relative_to(root.resolve()))
        except ValueError:
            continue
    return str(path)


def solc_semver(version_line):
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_line)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def compiler():
    """Return (path, version) for any solc with 0.7.0 <= version < 0.9.0."""
    for path in (os.environ.get("SOLC"), shutil.which("solc"), "/tmp/solc-0.8.26"):
        if not path or not Path(path).is_file():
            continue
        version = subprocess.run(
            [path, "--version"], check=True, capture_output=True, text=True
        ).stdout.strip().splitlines()[-1]
        semver = solc_semver(version)
        if semver is not None and SOLC_MIN <= semver < SOLC_MAX:
            return path, version
    raise ValueError(
        "Need solc with pragma range >=0.7.0 <0.9.0 "
        "(set SOLC or install solc on PATH)")


def require_file(path, label):
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")
    return path


def parse_signatures(text):
    """Parse solc --hashes output: 'a9059cbb: transfer(address,uint256)' -> selector map."""
    section, functions, events = None, {}, {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Function signatures"):
            section = functions
        elif line.startswith("Event signatures"):
            section = events
        elif section is not None and ":" in line:
            selector, signature = line.split(":", 1)
            section["0x" + selector.strip()] = signature.strip()
    return functions, events


def compile_one(solc, source, outdir):
    """Turn one .sol file into compiler artifacts via solc.

    Solidity source is human-readable text. solc compiles it to EVM bytecode:
    machine instructions the Ethereum Virtual Machine runs (PUSH, EQ, JUMPI, …).

    Flags used here:
      --bin-runtime  runtime bytecode only (code that remains after deployment;
                     excludes the one-time constructor/init code)
      --abi          JSON ABI (names, types, events)
      --hashes       four-byte function/event selectors from keccak256(signature)

    On disk after a successful run (example contract BlacklistToken):
      BlacklistToken.bin-runtime  hex string of runtime bytes (+ trailing metadata)
      BlacklistToken.abi          ABI JSON
      BlacklistToken.signatures   selector <-> name listing
    An interface-only file (IERC20) still emits ABI/hashes but often has empty
    runtime bytecode because there is no deployable implementation body.
    IERC20 is compiled separately as a teaching contrast; BlacklistToken does
    not import it and does not require it to build.

    This lab shells out to the same solc binary you can run in a terminal
    (subprocess.run). Equivalent CLI, for example:
      solc --bin-runtime --abi --hashes -o /tmp/out --overwrite BlacklistToken.sol
    """
    # Same argv as a direct shell command; Python only captures the files/exit code.
    proc = subprocess.run(
        [solc, "--bin-runtime", "--abi", "--hashes", "--pretty-json",
         "-o", str(outdir), "--overwrite", str(source)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise ValueError(proc.stderr.strip() or proc.stdout.strip())


def observe(outdir, source_file):
    """Build one evidence record: ABI names from solc, optional bytecode scan.

    Pipeline for bytecode-bearing contracts:
      .sol  --solc-->  hex runtime  -->  bytes  -->  strip metadata  -->  candidates()
    Interfaces may stop after ABI: zero runtime bytes, no scan.
    """
    names = sorted(path.stem for path in outdir.glob("*.bin-runtime"))
    if not names:
        raise ValueError(f"No compiler artifact from {source_file}")
    name = names[0]
    # Hex text from solc --bin-runtime (empty string => interface / no body).
    runtime_text = (outdir / f"{name}.bin-runtime").read_text().strip()
    functions, events = parse_signatures((outdir / f"{name}.signatures").read_text())
    record = {
        "contract": name, "source_file": source_file,
        "function_signatures": functions, "event_signatures": events,
        "abi_function_count": len(functions),
    }
    if not runtime_text:
        record.update({
            "runtime_bytes": 0, "runtime_sha256": None,
            "candidate_selectors": None, "scan_error": None,
            "limit": "No runtime bytecode. Selectors are compiler ABI names only.",
        })
        return record

    # Decode hex from solc into raw EVM bytes stored on-chain after deploy.
    raw = bytes.fromhex(runtime_text)

    # Runtime from solc is usually:  [ executable opcodes | CBOR metadata | 2-byte len ]
    # Metadata (compiler version, source hash, …) is not meant to execute. The last
    # two bytes are a big-endian length of the metadata blob (excluding those two
    # bytes). If the blob looks like a CBOR map (0xa1 / 0xa2 / 0xa3), set cut so
    # we scan only the executable prefix. Heuristic only—not full CBOR validation.
    size = int.from_bytes(raw[-2:], "big")
    suffix = raw[-size - 2:-2] if size + 2 < len(raw) else b""
    cut = len(raw) - size - 2 if suffix[:1] in (b"\xa1", b"\xa2", b"\xa3") else len(raw)

    # Linear scan for PUSH4 selector / EQ / PUSH dest / JUMPI / JUMPDEST patterns.
    try:
        hits, error = candidates(raw[:cut]), None
    except ValueError as exc:
        hits, error = None, str(exc)
    # Attach ABI names when the four-byte selector matches solc --hashes.
    for hit in hits or []:
        hit["abi_signature"] = functions.get(hit["selector"])
    record.update({
        "runtime_bytes": len(raw),
        "runtime_sha256": hashlib.sha256(raw).hexdigest(),
        "candidate_selectors": hits, "scan_error": error,
        "limit": ("candidate_selectors are bytecode dispatcher-pattern matches, "
                  "not blacklist membership checks; not reachability or behavior."),
    })
    return record


def layer_summary(label, source_path, digest, record):
    """Print source, ABI, and runtime as three separate evidence records."""
    abi_names = sorted(record["function_signatures"].values())
    selectors = record["candidate_selectors"]
    print(f"\n=== {label}: {record['contract']} ===")
    print("[1] SOURCE (Solidity text)")
    print(f"    file: {source_path.name}")
    print(f"    sha256: {digest}")
    print("[2] ABI (compiler function names / selectors)")
    print(f"    count: {record['abi_function_count']}")
    for selector, name in sorted(record["function_signatures"].items()):
        print(f"    {selector}  {name}")
    print("[3] RUNTIME BYTECODE (what nodes would execute)")
    print(f"    runtime_bytes: {record['runtime_bytes']}")
    if record["runtime_sha256"]:
        print(f"    runtime_sha256: {record['runtime_sha256']}")
    if selectors is None:
        print("    candidate_selectors: none (no runtime to scan)")
    else:
        print(f"    candidate_selectors: {len(selectors)} "
              "(dispatcher patterns in bytes; not blacklist checks)")
        for item in selectors:
            name = item.get("abi_signature") or "unresolved"
            print(f"    {item['selector']}  {name}  offset={item['offset']}")
    if record.get("scan_error"):
        print(f"    scan_error: {record['scan_error']}")
    return {"source_file": source_path.name, "source_sha256": digest,
            "abi_names": abi_names,
            "runtime_bytes": record["runtime_bytes"],
            "candidate_selector_count": None if selectors is None else len(selectors)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", type=Path, default=HERE / "IERC20.sol",
                        help="Teaching contrast: ERC-20 interface (ABI, usually 0 runtime); "
                             "not required to compile --token")
    parser.add_argument("--token", type=Path, default=HERE / "BlacklistToken.sol",
                        help="Standalone teaching token (does not import IERC20)")
    parser.add_argument("--out", type=Path, default=HERE / "data/stablecoin-case-report.json",
                        help="JSON report output")
    args = parser.parse_args()
    interface_src = require_file(args.interface, "interface")
    token_src = require_file(args.token, "token")
    solc, version = compiler()
    print("Learning goal: keep SOURCE, ABI, and RUNTIME BYTECODE as separate records.")
    print(f"Compiler: {version}")
    with tempfile.TemporaryDirectory(prefix="ch8-solc-") as tmp:
        root = Path(tmp)
        iface_dir, token_dir = root / "interface", root / "token"
        iface_dir.mkdir(); token_dir.mkdir()
        # .sol text -> solc artifacts (runtime hex, ABI, selector hashes)
        compile_one(solc, interface_src, iface_dir)
        compile_one(solc, token_src, token_dir)
        # artifacts -> separate SOURCE / ABI / RUNTIME fields in the report
        interface = observe(iface_dir, interface_src.name)
        token = observe(token_dir, token_src.name)
    hashes = {
        interface_src.name: hashlib.sha256(interface_src.read_bytes()).hexdigest(),
        token_src.name: hashlib.sha256(token_src.read_bytes()).hexdigest(),
    }
    layers = {
        "interface": layer_summary(
            "INTERFACE", interface_src, hashes[interface_src.name], interface),
        "token": layer_summary(
            "TOKEN", token_src, hashes[token_src.name], token),
    }
    report = {
        "kind": "local_solidity_compiler_observations",
        "compiler": version,
        "inputs": {"interface": relpath(interface_src), "token": relpath(token_src)},
        "output": relpath(args.out),
        "input_sha256": hashes,
        "sources": {
            interface_src.name: interface_src.read_text(),
            token_src.name: token_src.read_text(),
        },
        "interface": interface,
        "token": token,
        "evidence_layers": layers,
        "ai_status": "not run; deterministic compiler evidence only",
        "limit": ("Source text, ABI names, and runtime bytecode records are separate. "
                  "candidate_selectors are dispatcher patterns, not blacklist checks. "
                  "No chain state, reachability, or issuer identity."),
        "next_check": ("For a live specimen: obtain chain ID, address, and "
                       "block-pinned runtime before attributing control behavior."),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nWrote report: {relpath(args.out)}")
    print("Next (optional): explain_case_report.py summarizes these records only.")


if __name__ == "__main__":
    main()
