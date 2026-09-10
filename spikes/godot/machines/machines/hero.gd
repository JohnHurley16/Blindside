# ---------------------------------------------------------------------------
# BLINDSIDE -- THE machine. One of them, named once, checked everywhere.
#
# TRAILER.md 11.1 is the reason this file exists, and it is worth restating
# because it is a structural fault and not a production one:
#
#   the card at 0:46 says "you cannot drive IT", and nothing before it has
#   established what "it" is. Machines appear in six frames of act I and none
#   of them is THE machine. The fix is that the trailer follows ONE machine
#   from its first frame to its last, and 11.1 ends: "there is no mechanism for
#   that today -- the loadout and skin have to be part of the shot definition
#   and validated, in the same way the camera is."
#
# This is that mechanism. It lives in the shared machine layer, which is linked
# into every Godot project that shoots the trailer, so all of them are checking
# against ONE declaration rather than against three copies of a convention.
#
# HOW IT IS ENFORCED
#   1. A shot definition may carry a `machine` block (see FIELDS below).
#   2. Any block with `"role": "hero"` must name the identity in SPEC exactly.
#   3. Any shot whose trailer beat is in BEATS must carry a hero block.
#   4. A mismatch is a FAIL, reported with the value that caused it, in the
#      same list the camera's own failures go into, and it is NEVER quietly
#      corrected. That last rule is the cave rig's and it is inherited on
#      purpose: a validator that repairs its input teaches nobody anything.
# ---------------------------------------------------------------------------
class_name Hero
extends RefCounted

# ---------------------------------------------------------------------------
# THE PICK
# ---------------------------------------------------------------------------
# SURVEYOR, player team, default loadout, wear 0.35, undamaged.
#
# WHY THE SURVEYOR.
#   - It is the active season's chassis and `params.py` calls it "the default;
#     map and carry", so it is the machine a viewer will actually be handed.
#   - It is the only chassis that carries BOTH halves of what the trailer is
#     about: `active_sonar` and the `magnetometer` boom are how it learns the
#     cave, and `cargo_bay` plus `beacon_rack` are how it works it. The Scout
#     cannot carry, the Hauler is a lorry, the Swimmer is a Surveyor with the
#     boom taken off.
#   - It is legible. NOTES section 8's silhouette test found the Scout and the
#     Hauler unmistakable and the Surveyor and the Swimmer separable only by
#     loadout -- so a hero Surveyor WITH its default loadout is distinct from
#     everything else on the site, and a hero Swimmer would not be.
#   - It is 0.58 m long and rides at 0.32 m, which is the size TRAILER 8's
#     "machine height" camera band was measured against. Every machine-height
#     shot in both spikes is already framed for this chassis.
#
# WHY THE DEFAULT LOADOUT AND NOT `surveyor_bare`.
#   The bare variant exists for the loadout comparison and carries a lamp and
#   nothing else. For a machine that has to be recognised across twenty-nine
#   shots, the loadout IS the recognition -- the boom against the sky at the
#   collar is the same shape as the boom in the lamp pool underground.
#
# WHY PLAYER AND NOT RIVAL.
#   The pit-head is the player's site and the trailer is the player's raid.
#   ART 4.3: player is the pale shell over the graphite chassis with a
#   CONTINUOUS flank strip; the rival inverts the value and dashes the strip.
#   Both of those are read spatially, at any distance, in any light.
#
# WEAR 0.35, AND THIS ONE IS A GUESS.
#   11.1 asks for "one wear state" and nothing says which. 0.35 is the machine
#   layer's own default and it reads as a machine that has been down before and
#   come back -- mud to the hull seam, dust on the up-faces, the leading edges
#   scuffed to bare, and no panel gone. A clean machine says nobody has used
#   this; a 0.85 machine says this one is nearly finished. The trailer is about
#   whether THIS raid comes back, so the machine has to look like it has
#   survived others.
#
#   And it is ONE number for the whole cut, deliberately, even though a real
#   raid would dirty the machine as it went. A viewer does not notice wear
#   rising. A viewer absolutely notices it falling, and with twenty-nine shots
#   cut out of four projects in an order that is not chronological, any policy
#   other than "one value" will eventually cut a clean frame after a dirty one.
const SPEC := {
	"chassis": "surveyor",
	"model": "surveyor",        # the .glb prefix: `surveyor`, not `surveyor_bare`
	"loadout": "default",
	"skin": "player",
	"wear": 0.35,
	"damage": 0.0,
}

# The bay it lives in on the charge line, which is the bay TRAILER shot 5 shows
# EMPTY with its cable coiled -- because at 0:18 the machine is already on the
# bench being prepared, and at 0:22 we meet it there. The empty bay was already
# in the shot list; this only says whose it is.
const DOCK_BAY := 3

# Wear and damage are floats and a float comparison needs a tolerance. This is
# the tolerance, and it is tight enough that 0.35 and 0.4 are different
# machines, which they are.
const EPS := 0.005

# ---------------------------------------------------------------------------
# THE BEATS THAT MUST CONTAIN IT -- TRAILER.md section 3
# ---------------------------------------------------------------------------
# Read straight off the shot list. A beat is here if its one-line description
# names the machine as the subject of the frame.
#
#   6   "A machine on the bench ... First time we see one whole."   <- 11.1's shot
#   7   "the machine walking it"
#   12  "The machine walks the course alone"
#   13  "The machine steps onto the plate."
#   14  "Descending."                     (the machine is what is descending)
#   17  "Following the machine from behind"
#   18  the belief cut: the SAME camera as 17, so the same machine
#   22  "The machine loads."
#   27  "The machine walking, confident, in completely the wrong direction."
#
# Not here, and each for a reason a reader can check:
#   2,3,4   sky, yard, rain. No machine.
#   5       the charge line. Machines, but not this one -- its bay is the empty
#           one. This is the only beat where the hero's ABSENCE is the point.
#   16      "The lamp comes on. A passage resolves out of nothing." The lamp is
#           the machine's, but the frame is the passage; the machine is behind
#           the camera. See NOTE-16 in the cave shot list.
#   19,20,21,26  the belief register. The map, not the machine.
#   23,24,25     the Assayer. Not ours.
#   28      "The shaft, empty ... Nothing comes up." The machine's absence is
#           the entire shot and putting it in frame would destroy the ending.
const BEATS := ["6", "7", "12", "13", "14", "17", "18", "22", "27"]

# ---------------------------------------------------------------------------
# FIELDS a shot's `machine` block may carry
# ---------------------------------------------------------------------------
#   role      "hero" | "extra" | "none"        which machine this is.
#             Omit the whole block and the hero stands at home, in frame if the
#             frame reaches it. "none" takes it off the site for this shot.
#   chassis   scout | surveyor | hauler | swimmer
#   model     .glb prefix; defaults to chassis
#   loadout   "default" | "bare"
#   skin      "player" | "rival"
#   wear      0..1     ART 4.1's three masks, driven together
#   damage    0..1     ART 4.2's rungs
#   clip      walk | trot | idle | crouch
#   at        an anchor, or {"from": anchor, "to": anchor} to walk it
#   yaw       degrees, or "path" to face the way it is travelling
#   head      [yaw_deg, pitch_deg], an offset ON TOP of the clip
#   lamp      bool, default true
# The anchor grammar is the PROJECT's own -- the cave's {st,r,u,f} and the
# pit-head's {at,a,o,u} -- because where a machine stands is a fact about that
# place and not about the machine. This file validates IDENTITY only.
# ---------------------------------------------------------------------------

static func block(shot: Dictionary) -> Dictionary:
	var m = shot.get("machine", null)
	return m if m is Dictionary else {}


static func is_hero(shot: Dictionary) -> bool:
	return String(block(shot).get("role", "")) == "hero"


static func model_of(m: Dictionary) -> String:
	var ch: String = String(m.get("chassis", "surveyor"))
	if String(m.get("loadout", "default")) == "bare":
		return ch + "_bare"
	return String(m.get("model", ch))


## One line naming the machine in a shot, for the validation log. Every field
## that has to match is in it, so a continuity break is readable in the text
## report and not only in the picture.
static func describe(m: Dictionary) -> String:
	if m.is_empty():
		return "no machine block -- the project's default placement"
	if String(m.get("role", "")) == "none":
		return "NONE -- the hero is deliberately not on the site for this shot"
	return "%s %s/%s skin=%s wear=%.2f dmg=%.2f clip=%s" % [
		String(m.get("role", "extra")), String(m.get("chassis", "?")),
		String(m.get("loadout", "default")), String(m.get("skin", "?")),
		float(m.get("wear", -1.0)), float(m.get("damage", -1.0)),
		String(m.get("clip", "idle"))]


# ---------------------------------------------------------------------------
# THE CHECK
# ---------------------------------------------------------------------------
## Returns the failures, as strings, each carrying the value that caused it.
## An empty array is a pass. Nothing here writes to `shot`.
static func validate(shot: Dictionary) -> Array[String]:
	var out: Array[String] = []
	var beat: String = String(shot.get("trailer", ""))
	var m: Dictionary = block(shot)

	if m.is_empty():
		if BEATS.has(beat):
			out.append(("trailer beat %s must contain the hero machine " +
				"(TRAILER 3: it is the subject of that frame) and this shot " +
				"names no machine at all") % beat)
		return out

	var role: String = String(m.get("role", ""))
	if role == "none":
		# "the hero is NOT in this shot", said out loud. The default when a shot
		# carries no machine block at all is that the hero is standing at home on
		# the site, because it IS on the site -- so a shot that must not contain
		# it has to say so rather than rely on it being out of frame. TRAILER
		# shot 28 is the one that matters: the whole ending is that the shaft is
		# empty, and a Surveyor visible in the yard behind it destroys the cut.
		if BEATS.has(beat):
			out.append(("trailer beat %s must contain the hero machine and " +
				"this shot declares role 'none'") % beat)
		return out
	if role != "hero" and role != "extra":
		out.append("machine role '%s' is not 'hero', 'extra' or 'none'" % role)
		return out

	var ch: String = String(m.get("chassis", ""))
	if not Book.CHASSIS.has(ch):
		out.append("machine chassis '%s' is not one of %s" % [ch, str(Book.ORDER)])

	if role == "extra":
		if BEATS.has(beat):
			out.append(("trailer beat %s must contain the HERO machine and " +
				"this shot's machine is an extra (%s)") % [beat, describe(m)])
		# An extra that is identical to the hero is a continuity trap: it will
		# read as the hero in the cut and nothing will say otherwise.
		if _same(m):
			out.append(("an extra is identical to the hero (%s). Change one " +
				"of chassis / skin / wear, or make it the hero") % describe(m))
		return out

	# --- role == hero: every field must be the ONE machine -------------------
	for k in ["chassis", "loadout", "skin"]:
		var got: String = String(m.get(k, "<missing>"))
		if got != String(SPEC[k]):
			out.append("hero %s is '%s', the hero machine's %s is '%s'"
				% [k, got, k, String(SPEC[k])])
	for k2 in ["wear", "damage"]:
		var g: float = float(m.get(k2, -1.0))
		if absf(g - float(SPEC[k2])) > EPS:
			out.append("hero %s is %.3f, the hero machine's %s is %.3f"
				% [k2, g, k2, float(SPEC[k2])])
	if model_of(m) != String(SPEC["model"]):
		out.append("hero model resolves to '%s', the hero machine is '%s'"
			% [model_of(m), String(SPEC["model"])])
	var cl: String = String(m.get("clip", "idle"))
	if not Machine.CLIPS.has(cl):
		out.append("hero clip '%s' is not one of %s" % [cl, str(Machine.CLIPS)])
	if not m.has("at"):
		out.append("hero machine has no `at`: nothing says where it stands")
	return out


static func _same(m: Dictionary) -> bool:
	return (String(m.get("chassis", "")) == String(SPEC["chassis"])
		and String(m.get("skin", "")) == String(SPEC["skin"])
		and model_of(m) == String(SPEC["model"])
		and absf(float(m.get("wear", -1.0)) - float(SPEC["wear"])) <= EPS
		and absf(float(m.get("damage", -1.0)) - float(SPEC["damage"])) <= EPS)


# ---------------------------------------------------------------------------
# CROSS-SHOT: the check that a single shot cannot make
# ---------------------------------------------------------------------------
## Every hero block in a shot list, compared against SPEC and against each
## other. Returns lines for the report; empty means the whole list is one
## machine. Call it once per project after validating the shots individually,
## and call it in the ASSEMBLY over all three shot files -- which is the check
## 11.1 actually asks for, since the drift it describes is between projects.
static func audit(shots: Array, where: String) -> Array[String]:
	var out: Array[String] = []
	var n: int = 0
	for s in shots:
		if not (s is Dictionary):
			continue
		var f: Array[String] = validate(s)
		for x in f:
			out.append("%s/%s: %s" % [where, String(s.get("name", "?")), x])
		if is_hero(s):
			n += 1
	if n == 0:
		out.append("%s: no shot in this project names the hero machine" % where)
	return out


## The one line that says what the hero IS, for the head of every report.
static func banner() -> String:
	return ("HERO MACHINE: %s, %s loadout, %s skin, wear %.2f, damage %.2f  " +
		"(bay %d on the charge line)") % [String(SPEC["chassis"]),
		String(SPEC["loadout"]), String(SPEC["skin"]), float(SPEC["wear"]),
		float(SPEC["damage"]), DOCK_BAY]


# ---------------------------------------------------------------------------
# BUILDING ONE
# ---------------------------------------------------------------------------
## Spawn the machine a `machine` block describes. `ground` is the project's own
## floor query, `f(x, z) -> y`; without it the machine stands at y = 0 and does
## not respond to what is under its feet.
static func spawn(parent: Node3D, m: Dictionary, ground: Callable = Callable()) -> Machine:
	var mc := Machine.new()
	parent.add_child(mc)
	if ground.is_valid():
		mc.ground = ground
	mc.build(model_of(m), String(m.get("chassis", "surveyor")),
		"rival" if String(m.get("skin", "player")) == "rival" else "player",
		float(m.get("wear", 0.35)), float(m.get("damage", 0.0)))
	mc.lamp_on = bool(m.get("lamp", true))
	mc.set_clip(String(m.get("clip", "idle")))
	mc.walking = String(m.get("clip", "idle")) in ["walk", "trot"]
	var hd = m.get("head", null)
	if hd is Array and (hd as Array).size() == 2:
		mc.look_at_local(float(hd[0]), float(hd[1]))
	mc.refresh()
	return mc
