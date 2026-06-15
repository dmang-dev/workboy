#!/usr/bin/env python3
"""
apply_ses.py — import a Freerouting .ses session back into the placed board,
producing a fully-routed workboy.kicad_pcb. Run with KiCad's bundled Python:
    "<KiCad>/bin/python.exe" apply_ses.py
Then re-export Gerbers/drill from the routed board (see PCB_README.md).
"""
import os, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
brd = os.path.join(HERE, "workboy.kicad_pcb")
ses = os.path.join(HERE, "workboy.ses")

board = pcbnew.LoadBoard(brd)
ok = pcbnew.ImportSpecctraSES(board, ses)
pcbnew.SaveBoard(brd, board)
tracks = board.GetTracks().GetCount() if hasattr(board.GetTracks(), "GetCount") else len(list(board.GetTracks()))
print("SES import ok:", ok, "| track/via objects now:", tracks)
print("routed board saved ->", brd)
