# Why several clans' machines are in the same cave, and why they interfere

2026-09-09. The designer named the last hole in the fiction:

> "The only hole now is that this is obviously an online thing where different people's robots
> interact when they go in the cave. Why are there multiple different robots from different clans
> going down in the same cave? Why are they also trying to fight/steal sometimes?"

Two questions. This proposes an answer to each, built from decisions already made rather than
from new invention. Nothing here is decided; §7 lists what the designer has to rule on.

---

## 1. The short version

**Why the same cave:** the ice is retreating and it opens ways in. A newly open way is news, it is
finite, and it will not stay open. Everyone goes at once because being second is worth nothing.

**Why they interfere:** the valuable thing in the cave is not ore, it is **knowledge** — index
plates, downloads from the ancients' machinery, and the policies of machines that died down there.
Knowledge cannot be split, cannot be verified without using it, and a download that has been taken
is gone. That produces rivalry without anyone having to be a villain.

**And there is no combat.** A player cannot order a machine to do anything during a match, so
nobody can order an attack. What one clan can do to another is **lie to its machine**, which the
game already implements as the spoofed beacon. The rest is racing, blocking, salvage, and letting
the ancients' machinery do the killing.

---

## 2. Why the same cave, at the same time

This falls out of principle 10 and needs nothing new.

**The melt controls access.** In a world coming out of an ice age, a passage is not a place that
has always been there. It is a place the ice has just let go of. Meltwater cuts a moulin through
to an old working; a plug at the head of a drive gives way; a collapse settles as the ground
thaws. **A way in is an event, not a feature**, and it happens on the melt's schedule rather than
anyone's.

That gives every raid its premise without a word of explanation:

- **It is news.** A new opening on the valley wall is visible from a town built into that wall.
  Nobody has to be told; everybody can see it.
- **Being second is worth much less than being first.** §3 explains why: what is down there does
  not replenish.
- **It will close.** Meltwater rises through a season, the way refreezes, the working floods, the
  ground settles again. That is the match window and the extraction deadline, arrived at
  diegetically instead of as a rule.
- **It explains why the map is unknown to everyone.** Nobody has surveyed it because it did not
  exist last year. Every clan is equally blind, which is what makes the game fair and what makes
  drift matter.

**Guess:** that access events are frequent enough to sustain a game. A world early in a melt
plausibly opens many ways over a season; the frequency is a tuning question, not a fiction one.

---

## 3. Why they interfere: the loot cannot be shared

The obvious version of this game has clans competing over ore, and ore is a bad reason. It is
divisible, it is fungible, and a sensible society would agree a split. Everything actually
valuable in this cave has the opposite properties.

**Downloads are one-time.** `WHAT-HAPPENED-HERE.md` §4 puts six things in the ancients' machinery,
ordered by depth, and a machine takes them by putting its head to the floor. **A station that has
been read has been read.** Whoever gets there first has the block, the index fragment, or the piece
of the answer, and the second machine to arrive gets nothing. There is no version of that which two
clans share.

**The index is a jigsaw nobody holds.** `WHAT-HAPPENED-HERE.md` §3 makes the ancients' numbering a
real system that a player reconstructs from marks and downloads. Each clan holds a different
partial register. That has two consequences and both are load-bearing: nobody can plan a deep raid
alone, and **another clan's fragment is worth more than anything in the rock**, because it is the
only thing that turns depth from a gamble into a route.

**A wreck holds a policy, and a policy is tacit knowledge.** This is the strongest reason and it is
specific to this game. A dead machine leaves a wreck holding its cargo *and the behaviour it was
taught*. That behaviour is somebody's craft — a rule for when to turn back, when to freeze, when to
trust a fix — arrived at over many raids and many losses. **You cannot buy it, because you cannot
demonstrate it without giving it away, and you cannot verify it without running it.** So it gets
taken off wrecks rather than traded. A clan that recovers a rival's wreck learns how that rival
thinks.

**None of this requires anyone to be hostile.** Every one of these is a race, and a race produces
interference between decent people. That matters for tone: this is not a world of raiders. It is a
world where the thing worth having cannot be divided.

---

## 4. Why clans, and not companies

A guess, offered because the word the designer used is the right one.

Teaching a machine is not a procedure; it is a craft passed on. A clan is the unit that owns
machines, teaches them, and inherits the rules that worked. In a society recovering from an ice age
inside a valley, that is also simply what a household is. It gives the game its social unit for
free, it explains why rules are hoarded, and it explains why a stolen policy is an insult as well
as a loss.

It also sets the register of the rivalry. Clans in one valley are neighbours. They compete
constantly, ruinously, and without wanting each other dead — which is exactly the tone the
no-combat answer in §5 needs.

---

## 5. There is no combat, and that is the best part

**A player cannot order a machine to do anything during a match.** That is the game's one
invariant expressed as a rule: you teach beforehand and then you watch. So nobody can order an
attack. Whatever hostility exists has to be something a clan set up in advance, or something one
machine does to another's *understanding*.

What is left is better than combat:

- **Lying to a machine.** Already built. A cloned beacon says a name a rival machine trusts, and
  its map folds. `THE-SENSOR-AND-SLAM.md` §3 explains why it works: the machine localises against
  markers it identifies by name and never checks geometry. This is the game's real weapon, and it
  attacks belief rather than the body.
- **Being heard.** `SOUND-DESIGN.md`: sonar is loud and announces your position to every passive
  listener. Using your best sensor tells everyone where you are. That is a strategic cost with no
  shooting in it at all.
- **Racing and blocking.** Depth is finite and one-time; arriving first is the whole fight.
- **The ancients do the killing.** The Assayer is lethal on a contour, and a machine that has been
  walked off its route by a lie can end up standing in it. **Nobody has to build a weapon, because
  the world already has one, and the way to use it is to make somebody else's machine walk into
  it.** That is a horrible thing to do to a neighbour and it is completely deniable.
- **Salvage.** A wreck is a resource, and recovering one is a raid objective rather than an act of
  violence.

**Design consequence, stated plainly:** if this holds, the game should never add a weapon. The
moment a machine can be told to attack, the invariant is dead, because directing an attack is
control. Everything above works precisely because it is arranged in advance and resolves without
the player.

---

## 6. What the trailer and the fiction gain

- The rival's beacon at 2:20 stops being an arbitrary antagonist and becomes a neighbour doing
  what neighbours do when a way opens and there is one download at the bottom of it.
- The extraction window stops being a rule and becomes the melt.
- `DESIGN-PRINCIPLES.md` §2's "you lose stuff if you don't get out" gains its sharpest form: what
  you lose is not cargo, it is what you taught.
- And the first act of the trailer gains a shot it did not have: **other machines going down too.**

---

## 7. What the designer has to rule on

Each yes/no, with a recommended default.

1. **Access is opened by the melt, and a match is a newly opened way.** *Recommend: yes.* It
   supplies the premise, the window and the shared ignorance at no cost.
2. **The valuable loot is knowledge — downloads, index, policies — rather than ore.** *Recommend:
   yes.* Ore may still exist as ballast; it is not what the game is about.
3. **A download taken is taken, permanently, per station.** *Recommend: yes.* This is the whole
   reason arriving second is worse.
4. **A wreck yields the policy the machine was taught, to whoever recovers it.** *Recommend: yes*,
   and note it is already in the design as wrecks; this makes it the point rather than a detail.
5. **The social unit is the clan, and rules are inherited craft.** *Recommend: yes.*
6. **There is never a weapon, and hostility is exclusively deception, racing, salvage, and the
   ancients' machinery.** *Recommend: yes*, and this is the one worth being certain about, because
   it is very hard to reverse once a weapon exists.
7. **Rivals are neighbours rather than enemies.** *Recommend: yes*, for tone.
8. **Do clans ever cooperate formally** — shared index, joint raids? *Recommend: not at launch*,
   but the index jigsaw makes it the obvious first social feature.

---

## 8. Guesses

- That access events are frequent enough to sustain matchmaking.
- That a clan is a household rather than a guild or a company.
- That the index fragments are distributed rather than centrally held.
- That policy theft off a wreck is technically expressible — it assumes a policy is a portable
  artefact, which `ARCHITECTURE.md` supports but nothing has tested.
- That the melt window and the eight-minute match are the same clock at different scales.
- That players will read racing-and-deception as competition rather than as a missing feature. This
  is the biggest guess in the document and only a playtest answers it.
