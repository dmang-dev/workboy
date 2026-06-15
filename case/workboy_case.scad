/* ===========================================================================
 * WorkBoy keyboard — parametric 3D case
 * ---------------------------------------------------------------------------
 * Two-piece clamshell: a top plate with key cutouts + a bottom tray with PCB
 * standoffs, screw bosses (heat-set inserts) and a rear cable slot.
 *
 * Key positions come from layout/keymap.py via the generated key_positions.scad
 * (run: python layout/gen_layout.py). The build123d port (workboy_case_b123d.py)
 * is the CI-tested path and can also import the KiCad board STEP.
 *
 * Render:  set `part` then F6, or from CLI:
 *   openscad -D 'part="top"'    -o workboy_top.stl    workboy_case.scad
 *   openscad -D 'part="bottom"' -o workboy_bottom.stl workboy_case.scad
 * =========================================================================== */

part = "both";          // "top" | "bottom" | "both"
$fn  = 48;

include <key_positions.scad>   // generated: pitch, field_w, field_h, key_pos[]

key_gap = 2.0;          // plate cutout = key cell minus this (cap clearance)

/* ---- shell ---- */
margin     = 8;
plate_th   = 2.0;
wall       = 2.4;
floor_th   = 2.0;
case_h     = 20;        // floor top -> plate underside (internal height)
standoff_h = 6.0;       // PCB rests this high (clears THT lead tails)
pcb_inset  = 7;         // PCB standoff inset from the outer edge

/* ---- fasteners (M2.5 + heat-set inserts) ---- */
screw_d   = 2.9;        // M2.5 free-fit shaft clearance (FDM)
boss_od   = 7;          // screw-boss outer diameter
insert_d  = 3.4;        // heat-set insert pocket dia (VERIFY vs your inserts)

/* ---- derived ---- */
case_w = field_w + 2 * margin;
case_d = field_h + 2 * margin;
cox = case_w/2 - boss_od/2 - wall*0.5;   // boss X (overlaps wall for a solid join)
coy = case_d/2 - boss_od/2 - wall*0.5;   // boss Y

module rrect(w, d, r) offset(r = r) square([w - 2*r, d - 2*r], center = true);

/* cut one rectangle per key at its real centre (key_pos = [[cx,cy,w_units],..]) */
module key_field(h) {
    for (k = key_pos)
        translate([k[0], k[1], -0.5])
            linear_extrude(h + 1)
                square([k[2] * pitch - key_gap, pitch - key_gap], center = true);
}

module corners(ox, oy) {
    for (x = [-ox, ox]) for (y = [-oy, oy]) translate([x, y, 0]) children();
}

module bottom_shell() {
    difference() {
        linear_extrude(case_h) rrect(case_w, case_d, 2);                  // block
        translate([0, 0, floor_th])
            linear_extrude(case_h - floor_th + 0.1) rrect(case_w - 2*wall, case_d - 2*wall, 2); // hollow
        translate([0, case_d/2 - wall, case_h - 6])                      // cable slot
            cube([12, wall*3, 8], center = true);
    }
    // screw bosses (heat-set insert pocket at top)
    corners(cox, coy) difference() {
        cylinder(h = case_h, d = boss_od);
        translate([0, 0, case_h - 8]) cylinder(h = 8.1, d = insert_d);
    }
    // PCB standoffs (inboard, clear of the corner screw bosses)
    corners(case_w/2 - (boss_od + pcb_inset), case_d/2 - (boss_od + pcb_inset))
        cylinder(h = floor_th + standoff_h, d = 5);
}

module top_plate() {
    difference() {
        translate([0, 0, case_h]) linear_extrude(plate_th) rrect(case_w, case_d, 2);
        translate([0, 0, case_h]) key_field(plate_th);
        // screw clearance + countersink at each boss
        corners(cox, coy) translate([0, 0, case_h - 0.5])
            cylinder(h = plate_th + 1, d = screw_d);
        corners(cox, coy) translate([0, 0, case_h + plate_th - 1.2])
            cylinder(h = 1.4, d1 = screw_d, d2 = screw_d + 2.4);
    }
}

if (part == "bottom" || part == "both") color("Gainsboro")   bottom_shell();
if (part == "top"    || part == "both") color("LightSkyBlue") top_plate();
