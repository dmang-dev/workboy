#!/usr/bin/env python3
"""
run_ci.py — tiny CI runner for the WorkBoy project.

Runs every check that has its toolchain available and SKIPs the rest cleanly:
  1. protocol-sim    (always; pure Python)
  2. rom-build       (GBDK-2020 lcc)
  3. firmware-build  (PlatformIO + avr-gcc)
  4. case-export     (build123d -> STL/STEP)

Exit code = number of FAILED steps (0 = all green). SKIPs do not fail the run.
"""
import os, sys, shutil, subprocess, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def have(mod):
    return importlib.util.find_spec(mod) is not None


def find_lcc():
    cands = [os.path.join(ROOT, "tools", "gbdk", "bin", "lcc.exe"),
             os.path.join(ROOT, "tools", "gbdk", "bin", "lcc")]
    g = os.environ.get("GBDK_HOME")
    if g:
        cands += [os.path.join(g, "bin", "lcc.exe"), os.path.join(g, "bin", "lcc")]
    for p in cands:
        if os.path.exists(p):
            return p
    return shutil.which("lcc")


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


results = []
def step(name, status, detail=""):
    results.append(status)
    print(f"  [{status:4}] {name}" + (f"  ({detail})" if detail else ""))


print("WorkBoy CI")

# 1) protocol simulation
rc, out = run([sys.executable, os.path.join(ROOT, "tests", "protocol_sim.py")])
last = out.splitlines()[-1] if out else ""
step("protocol-sim", "PASS" if rc == 0 else "FAIL", last)

# 2) ROM build (GBDK-2020)
lcc = find_lcc()
if not lcc:
    step("rom-build", "SKIP", "GBDK lcc not found")
else:
    romdir = os.path.join(ROOT, "rom")
    srcs = [os.path.join("src", f) for f in
            ("main.c", "workboy_link.c", "scancodes.c", "phonebook.c",
             "ui.c", "calc.c", "clock.c")]
    rc, out = run([lcc, "-Wl-yt0x03", "-Wl-ya4", "-Wl-yo8",
                   "-o", "workboy_homebrew.gb"] + srcs, cwd=romdir)
    gb = os.path.join(romdir, "workboy_homebrew.gb")
    ok = rc == 0 and os.path.exists(gb)
    step("rom-build", "PASS" if ok else "FAIL",
         f"{os.path.getsize(gb)} bytes" if ok else out[-160:])

# 3) firmware build (PlatformIO)
if not have("platformio"):
    step("firmware-build", "SKIP", "platformio not installed")
else:
    rc, out = run([sys.executable, "-m", "platformio", "run"],
                  cwd=os.path.join(ROOT, "firmware"))
    step("firmware-build", "PASS" if rc == 0 else "FAIL",
         "" if rc == 0 else out[-160:])

# 4) case export (build123d)
#
# Do NOT regenerate a placeholder board STEP here. This step used to run
# kicad/make_board_step.py first, which overwrote the REAL exported board with a
# 144 x 78 mm rectangle - so CI silently destroyed the export the case is fitted
# to. That script is gone; produce the real one with:
#     kicad-cli pcb export step --output kicad/workboy_board.step kicad/workboy.kicad_pcb
# The case script derives all of its dimensions from kicad/workboy.kicad_pcb and
# only uses the STEP for the visual assembly, so it runs fine without one.
if not have("build123d"):
    step("case-export", "SKIP", "build123d not installed")
else:
    rc, out = run([sys.executable, os.path.join(ROOT, "case", "workboy_case_b123d.py")])
    ok = rc == 0 and os.path.exists(os.path.join(ROOT, "case", "workboy_top.stl"))
    step("case-export", "PASS" if ok else "FAIL", "" if ok else out[-160:])

p = results.count("PASS"); s = results.count("SKIP"); f = results.count("FAIL")
print("-" * 40)
print(f"{p} passed, {s} skipped, {f} failed")
sys.exit(f)
