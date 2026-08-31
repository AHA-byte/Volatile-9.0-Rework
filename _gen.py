#!/usr/bin/env python3
"""Generate wares.xml, equipmentmods.xml and volatile_mods.xml (MD) for
Volatile Mods v9.00 XP system.

41 levels (lv0..lv40) x 4 categories (shield, engine, weapon, hull).
"""
import os

ROOT     = os.path.dirname(__file__)
LIB_DIR  = os.path.join(ROOT, "libraries")
MD_DIR   = os.path.join(ROOT, "md")

CATEGORIES = ["shield", "engine", "weapon", "hull"]
MAX_LEVEL = 40

# Per-category Tuning Software cost. Distinct values used as a fingerprint:
# event_inventory_removed event.param[ware.modpart_tuningsoftware] == amount
# removed in one craft, mapping uniquely to a category. Values must stay
# distinct from each other and from common vanilla mod TS costs (typically 1-5).
TS_COST = {
    "shield": 13,
    "engine": 11,
    "weapon": 10,
    "hull":   12,
}

def linear_range(N):
    # Shift the whole curve up so Level 0 starts at +3% (1.03)
    # L0 = +3%, L1 = +6%, ..., L44 = +135%
    #.03=1.2
    #.04=1.6
    #.025=1.0(100%)
    val = 1.25 + (N * 0.025)
    
    # Add a custom capstone bonus for the final level to hit exactly +85% (1.85)
    # Bonus for getting max
    if N == MAX_LEVEL:
        val = 2.25
        
    return (val, val)

def weapon_range(N):   return linear_range(N)
def engine_range(N):   return linear_range(N)
def hull_range(N):     return linear_range(N)
def shield_range(N):   return linear_range(N)

RANGES = {
    "shield": shield_range,
    "engine": engine_range,
    "weapon": weapon_range,
    "hull":   hull_range,
}

PACK_DESCRIPTIONS = {
    "shield": "Deterministic shield upgrade. Increases capacity and recharge rate; decreases recharge delay.",
    "engine": "Deterministic engine upgrade. Increases thrust, rotation, and strafe; decreases charge times.",
    "weapon": "Deterministic weapon upgrade. Increases damage, cooling, reload, and speed; decreases charge time.",
    "hull":   "Deterministic hull upgrade. Increases hull and radar range; decreases mass and drag.",
}

PACK_TITLE = {
    "shield": "Volatile Shield Mod",
    "engine": "Volatile Engine Mod",
    "weapon": "Volatile Weapon Mod",
    "hull":   "Volatile Hull Mod",
}

# ---------------- wares.xml ----------------
def gen_wares():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<diff xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
           '  <add sel="/wares">',
           '    <!-- Volatile Mods XP system: 4 categories x 41 levels (lv0..lv40).',
           '         Per-category TS cost (Shield 10, Engine 8, Weapon 7, Hull 9)',
           '         doubles as a craft-detection fingerprint for the XP system.',
           '         Blueprints are gated: only lv0..currentLevel are unlocked via the MD XP system. -->',
           '']
    for cat in CATEGORIES:
        ts_cost = TS_COST[cat]
        out.append(f'    <!-- ========================== {cat.upper()} PACKS (cost: {ts_cost} TS) ========================== -->')
        for N in range(MAX_LEVEL + 1):
            ware_id = f"mod_{cat}_volatile_basic_lv{N}"
            mn, mx  = RANGES[cat](N)
            name    = f"{PACK_TITLE[cat]} (lv{N})"
            pct_val = round((mn - 1.0) * 100)
            rng_str = f"+{pct_val}%"
            desc    = f"{PACK_DESCRIPTIONS[cat]} Level {N} bonus: {rng_str}. Apply cost: {ts_cost} Tuning Software. Permanent once applied."
            base    = 15000 + N * 3000
            avg     = 20000 + N * 4000
            mx_p    = 30000 + N * 6000
            out.append(f'    <ware id="{ware_id}" name="{name}" description="{desc}" transport="inventory" volume="1" tags="crafting equipmentmod">')
            out.append(f'      <price min="{base}" average="{avg}" max="{mx_p}"/>')
            out.append( '      <production time="60" amount="1" method="default" name="{20206,301}">')
            out.append( '        <primary>')
            out.append(f'          <ware ware="modpart_tuningsoftware" amount="{ts_cost}"/>')
            out.append( '        </primary>')
            out.append( '      </production>')
            out.append( '    </ware>')
        out.append('')
    out.append('  </add>')
    out.append('</diff>')
    return "\n".join(out) + "\n"

# ---------------- equipmentmods.xml ----------------
SHIELD_BONUS = ["rechargerate", "rechargedelay"]
ENGINE_BONUS = ["boostthrust", "boostduration", "travelthrust", "boostacc",
                "travelattacktime", "travelchargetime", "strafeacc",
                "rotationthrust", "strafethrust"]
WEAPON_BONUS = ["cooling", "reload", "speed", "beamlength", "lifetime",
                "chargetime", "rotationspeed", "sticktime", "surfaceelement"]
HULL_BONUS   = ["mass", "drag", "radarrange"]

def gen_equipmentmods():
    def fmt(x): return f"{x:.2f}"
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<diff xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
           '  <!--',
           '    Volatile Mods v9.00 - XP leveled variants (lv0..lv40 per category).',
           '    Range widens upward only per level (max += 0.01). Shield exception: on',
           '    even levels the min also shifts upward by +0.01 (shrinks the penalty).',
           '      Weapon/Engine lv N: 0.85 .. 1.30 + N*0.01',
           '      Hull       lv N:   0.80 .. 1.30 + N*0.01',
           '      Shield     lv N:   0.60 + floor(N/2)*0.01 .. 1.60 + N*0.01',
           '    Per-category TS craft cost: Shield 13, Engine 11, Weapon 10, Hull 12.',
           '  -->',
           '']

    INVERTED_STATS = {"rechargedelay", "travelchargetime", "travelattacktime", "mass", "drag", "chargetime"}

    def block(sel, outer_tag, bonus_stats, range_fn, cat):
        out.append(f'  <add sel="{sel}">')
        for N in range(MAX_LEVEL + 1):
            mn, mx = range_fn(N)
            ware_id = f"mod_{cat}_volatile_basic_lv{N}"
            
            # The outer tag (capacity, forwardthrust) always scales positively
            out.append(f'    <{outer_tag} ware="{ware_id}" quality="1" min="{fmt(mn)}" max="{fmt(mx)}">')
            out.append(f'      <bonus chance="1.0" max="{len(bonus_stats)}">')
            for stat in bonus_stats:
                if stat in INVERTED_STATS:
                    # Invert the math so an 80% buff (1.80) becomes a reduction (1.0 / 1.80 = 0.55x)
                    inv_val = 1.0 / mn
                    out.append(f'        <{stat} min="{fmt(inv_val)}" max="{fmt(inv_val)}" weight="1"/>')
                else:
                    out.append(f'        <{stat} min="{fmt(mn)}" max="{fmt(mx)}" weight="1"/>')
            out.append(f'      </bonus>')
            out.append(f'    </{outer_tag}>')
        out.append('  </add>')
        out.append('')

    out.append('  <!-- ============================ SHIELD ============================ -->')
    block('/equipmentmods/shield', 'capacity',      SHIELD_BONUS, shield_range, 'shield')
    out.append('  <!-- ============================ ENGINE ============================ -->')
    block('/equipmentmods/engine', 'forwardthrust', ENGINE_BONUS, engine_range, 'engine')
    out.append('  <!-- ============================ WEAPON ============================ -->')
    out.append('  <!-- mining is a flat-yield stat, intentionally skipped. -->')
    block('/equipmentmods/weapon', 'damage',        WEAPON_BONUS, weapon_range, 'weapon')
    out.append('  <!-- ============================ SHIP (HULL) ============================ -->')
    block('/equipmentmods/ship',   'maxhull',       HULL_BONUS,   hull_range,   'hull')

    # NOTE: TS costs (Shield 13, Engine 11, Weapon 10, Hull 12) are wired in two
    # other places that must stay in sync: gen_wares() reads TS_COST directly,
    # and the PollForCraft cue in gen_md() hardcodes the amount->category map.

    out.append('</diff>')
    return "\n".join(out) + "\n"

# ---------------- md/volatile_mods.xml ----------------
def ware_list_literal(cat, indent):
    """Return a multi-line XML list literal with 41 ware refs."""
    entries = [f"ware.mod_{cat}_volatile_basic_lv{N}" for N in range(MAX_LEVEL + 1)]
    pad = " " * indent
    joined = (",\n" + pad).join(entries)
    return "[\n" + pad + joined + "\n" + " " * (indent - 2) + "]"

def gen_md():
    # Pre-build ware lists for each category (as multi-line string literals)
    wl = {cat: ware_list_literal(cat, indent=14) for cat in CATEGORIES}
    return f'''<?xml version="1.0" encoding="utf-8"?>
<mdscript name="VolatileMods" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="md.xsd">
  <!--
    Volatile Mods for v9.00 - Nemesystem
    ====================================
    Basic-only gambler mods with per-category XP progression (lv0..lv40).

    Flow:
      1. Buy a Volatile pack (Shield/Engine/Weapon/Hull lv<N>) at an equipment
         dock. Only lv0..currentLevel blueprints are unlocked per category.
      2. Apply at the dock; the vanilla apply rolls every stat uniformly in the
         level's range and bakes them permanently.
      3. Each CRAFT of a volatile pack grants XP to that category;
         reaching the XP threshold unlocks the next level's blueprint.

    XP curve (delta to reach lv(N+1) from lvN): 10 + 5 * N.
      lv0 -> lv1: 10, lv1 -> lv2: 15, lv2 -> lv3: 20, lv3 -> lv4: 25, ...
      lv39 -> lv40: 205. Cumulative XP to reach lv40: sum = 4300.
    XP gain per craft: random(1 .. 5 + currentLevel).

    Craft detection: each category has a unique TS cost (Shield 13, Engine 11,
    Weapon 10, Hull 12). On event_inventory_removed for modpart_tuningsoftware,
    event.param[ware.modpart_tuningsoftware] (amount removed) maps directly
    to the crafted category.
    Equipment mod packs do NOT land in player.entity.inventory in X4 9.0
    (workbench applies them directly), so this fingerprint approach replaces
    the earlier polling-based detection.

    Extras: per-size Tuning Software drop on player kill. Slider values are
    "expected TS x 100": 100 = guaranteed 1, 200 = guaranteed 2, 50 = 50%
    chance of 1. Defaults: S=10, M=50, L=100, XL=200.
    Debug toggles for drop notifications and craft XP ticker.
  -->
  <cues>

    <cue name="Init" instantiate="false">
      <actions>
        <set_value name="global.$VolatileMods" exact="table[]"/>

        <!-- Debug toggles -->
        <set_value name="global.$VolatileMods.$Debug" exact="false"/>
        <set_value name="global.$VolatileMods.$CraftXPNotify" exact="false"/>

        <!-- Tuning Software drop yield per ship-kill, by ship size class.
             Slider value semantics: "expected TS × 100".
               <100  = chance to drop 1 TS (e.g. 50 = 50% chance of 1).
                100  = guaranteed 1 TS.
                200  = guaranteed 2 TS.
                150  = guaranteed 1 + 50% chance of a 2nd.
             Defaults: S=10%, M=50%, L=100% (=1), XL=200% (=2). -->
        <set_value name="global.$VolatileMods.$TSDropS"  exact="10"/>
        <set_value name="global.$VolatileMods.$TSDropM"  exact="50"/>
        <set_value name="global.$VolatileMods.$TSDropL"  exact="100"/>
        <set_value name="global.$VolatileMods.$TSDropXL" exact="200"/>

        <!-- Per-category XP and Level (0..40). -->
        <set_value name="global.$VolatileMods.$XP" exact="table[]"/>
        <set_value name="global.$VolatileMods.$Level" exact="table[]"/>
        <set_value name="global.$VolatileMods.$XP.$shield" exact="0"/>
        <set_value name="global.$VolatileMods.$XP.$engine" exact="0"/>
        <set_value name="global.$VolatileMods.$XP.$weapon" exact="0"/>
        <set_value name="global.$VolatileMods.$XP.$hull"   exact="0"/>
        <set_value name="global.$VolatileMods.$Level.$shield" exact="0"/>
        <set_value name="global.$VolatileMods.$Level.$engine" exact="0"/>
        <set_value name="global.$VolatileMods.$Level.$weapon" exact="0"/>
        <set_value name="global.$VolatileMods.$Level.$hull"   exact="0"/>

        <!-- Ware lists per category (index i = lv(i-1) in X4 1-based lists). -->
        <set_value name="global.$VolatileMods.$Wares" exact="table[]"/>
        <set_value name="global.$VolatileMods.$Wares.$shield" exact="{wl['shield']}"/>
        <set_value name="global.$VolatileMods.$Wares.$engine" exact="{wl['engine']}"/>
        <set_value name="global.$VolatileMods.$Wares.$weapon" exact="{wl['weapon']}"/>
        <set_value name="global.$VolatileMods.$Wares.$hull"   exact="{wl['hull']}"/>

        <debug_text text="'MOD: VolatileMods -- Init defaults set.'" context="false" filter="scripts"/>

        <!-- Grant lv0 blueprints. Higher levels unlocked via XP gain. -->
        <add_blueprints wares="[
            ware.mod_shield_volatile_basic_lv0,
            ware.mod_engine_volatile_basic_lv0,
            ware.mod_weapon_volatile_basic_lv0,
            ware.mod_hull_volatile_basic_lv0
          ]"/>
        <debug_text text="'MOD: VolatileMods -- Lv0 blueprints granted for 4 categories.'" context="false" filter="scripts"/>
      </actions>

      <cues>

        <!-- Save-compat: restore any variables missing from older saves and
             rebuild ware lists (lists aren't save-persisted). -->
        <cue name="CheckVariablesExist" instantiate="true" version="10">
          <conditions>
            <check_any>
              <event_universe_generated/>
              <event_game_loaded/>
            </check_any>
          </conditions>
          <actions>
            <debug_text text="'MOD: VolatileMods -- CheckVariablesExist START.'" context="false" filter="scripts"/>
            <do_if value="not global.$VolatileMods?">
              <set_value name="global.$VolatileMods" exact="table[]"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$Debug?">
              <set_value name="global.$VolatileMods.$Debug" exact="false"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$CraftXPNotify?">
              <set_value name="global.$VolatileMods.$CraftXPNotify" exact="false"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$TSDropS?">
              <set_value name="global.$VolatileMods.$TSDropS" exact="10"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$TSDropM?">
              <set_value name="global.$VolatileMods.$TSDropM" exact="50"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$TSDropL?">
              <set_value name="global.$VolatileMods.$TSDropL" exact="100"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$TSDropXL?">
              <set_value name="global.$VolatileMods.$TSDropXL" exact="200"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$XP?">
              <set_value name="global.$VolatileMods.$XP" exact="table[]"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$Level?">
              <set_value name="global.$VolatileMods.$Level" exact="table[]"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$XP.$shield?">
              <set_value name="global.$VolatileMods.$XP.$shield" exact="0"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$XP.$engine?">
              <set_value name="global.$VolatileMods.$XP.$engine" exact="0"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$XP.$weapon?">
              <set_value name="global.$VolatileMods.$XP.$weapon" exact="0"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$XP.$hull?">
              <set_value name="global.$VolatileMods.$XP.$hull" exact="0"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$Level.$shield?">
              <set_value name="global.$VolatileMods.$Level.$shield" exact="0"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$Level.$engine?">
              <set_value name="global.$VolatileMods.$Level.$engine" exact="0"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$Level.$weapon?">
              <set_value name="global.$VolatileMods.$Level.$weapon" exact="0"/>
            </do_if>
            <do_if value="not global.$VolatileMods.$Level.$hull?">
              <set_value name="global.$VolatileMods.$Level.$hull" exact="0"/>
            </do_if>

            <!-- Re-build ware lists (not save-persisted). -->
            <set_value name="global.$VolatileMods.$Wares" exact="table[]"/>
            <set_value name="global.$VolatileMods.$Wares.$shield" exact="{wl['shield']}"/>
            <set_value name="global.$VolatileMods.$Wares.$engine" exact="{wl['engine']}"/>
            <set_value name="global.$VolatileMods.$Wares.$weapon" exact="{wl['weapon']}"/>
            <set_value name="global.$VolatileMods.$Wares.$hull"   exact="{wl['hull']}"/>

            <debug_text text="'MOD: VolatileMods -- CheckVariablesExist DONE. Levels shield=%s engine=%s weapon=%s hull=%s'.[global.$VolatileMods.$Level.$shield, global.$VolatileMods.$Level.$engine, global.$VolatileMods.$Level.$weapon, global.$VolatileMods.$Level.$hull]" context="false" filter="scripts"/>
          </actions>
        </cue>

        <!-- Tuning Software drop on player kill, by ship size class. -->
        <cue name="TuningSoftwareDrop" instantiate="true">
          <conditions>
            <event_player_killed_object/>
          </conditions>
          <actions>
            <do_if value="event.param.exists and event.param.isclass.ship">
              <!-- Resolve per-size yield setting. Order largest-first (precise isclass). -->
              <set_value name="$pct" exact="0"/>
              <set_value name="$sizeTag" exact="'?'"/>
              <do_if value="event.param.isclass.ship_xl">
                <set_value name="$pct" exact="global.$VolatileMods.$TSDropXL"/>
                <set_value name="$sizeTag" exact="'XL'"/>
              </do_if>
              <do_elseif value="event.param.isclass.ship_l">
                <set_value name="$pct" exact="global.$VolatileMods.$TSDropL"/>
                <set_value name="$sizeTag" exact="'L'"/>
              </do_elseif>
              <do_elseif value="event.param.isclass.ship_m">
                <set_value name="$pct" exact="global.$VolatileMods.$TSDropM"/>
                <set_value name="$sizeTag" exact="'M'"/>
              </do_elseif>
              <do_elseif value="event.param.isclass.ship_s">
                <set_value name="$pct" exact="global.$VolatileMods.$TSDropS"/>
                <set_value name="$sizeTag" exact="'S'"/>
              </do_elseif>

              <do_if value="$pct gt 0">
                <!-- Slider semantics: pct = "expected TS × 100".
                     guaranteed = pct / 100; remainder = pct - guaranteed*100 (X4 MD has no mod operator). -->
                <set_value name="$guaranteed" exact="$pct / 100"/>
                <set_value name="$remainder"  exact="$pct - ($pct / 100) * 100"/>
                <set_value name="$bonus" exact="0"/>
                <set_value name="$roll"  exact="0"/>
                <do_if value="$remainder gt 0">
                  <set_value name="$roll" min="1" max="100"/>
                  <do_if value="$roll le $remainder">
                    <set_value name="$bonus" exact="1"/>
                  </do_if>
                </do_if>
                <set_value name="$total" exact="$guaranteed + $bonus"/>

                <do_if value="$total gt 0">
                  <add_inventory entity="player.entity" ware="ware.modpart_tuningsoftware" exact="$total"/>
                  <set_value name="$tsTotal" exact="player.entity.inventory.{{ware.modpart_tuningsoftware}}.count"/>
                  <debug_text text="'MOD: VolatileMods -- TS DROPPED size=%s yield=%s%% guaranteed=%s bonus=%s (roll=%s/%s) total=%s. Inventory=%s.'.[$sizeTag, $pct, $guaranteed, $bonus, $roll, $remainder, $total, $tsTotal]" context="false" filter="scripts"/>
                  <do_if value="global.$VolatileMods.$Debug">
                    <show_notification text="[
                        'Volatile Mods',
                        '%s ship: +%s Tuning Software (yield %s%%). Inventory: %s.'.[$sizeTag, $total, $pct, $tsTotal]
                      ]" timeout="4s" priority="3"/>
                  </do_if>
                </do_if>
                <do_else>
                  <debug_text text="'MOD: VolatileMods -- TS drop MISS size=%s yield=%s%% (roll=%s gt %s).'.[$sizeTag, $pct, $roll, $remainder]" context="false" filter="scripts"/>
                  <do_if value="global.$VolatileMods.$Debug">
                    <show_notification text="[
                        'Volatile Mods',
                        '%s ship: no drop (yield %s%%, roll %s/%s).'.[$sizeTag, $pct, $roll, $remainder]
                      ]" timeout="3s" priority="2"/>
                  </do_if>
                </do_else>
              </do_if>
            </do_if>
          </actions>
        </cue>

        <!-- Craft detection via TS-cost fingerprint.
             Each volatile category has a unique TS production cost
             (Shield 13, Engine 11, Weapon 10, Hull 12). When the player
             crafts a volatile mod pack, exactly that many Tuning Software
             units are removed in a single event. event.param is a
             {{ware: amount}} table; we look up modpart_tuningsoftware in it
             and map the amount to a category. -->
        <cue name="PollForCraft" instantiate="true">
          <conditions>
            <event_inventory_removed object="player.entity" ware="ware.modpart_tuningsoftware"/>
          </conditions>
          <actions>
            <!-- X4 MD uses == for equality (not eq in this context). -->
            <set_value name="$amount" exact="if event.param.{{ware.modpart_tuningsoftware}}? then event.param.{{ware.modpart_tuningsoftware}} else 0"/>
            <debug_text text="'MOD: VolatileMods -- PollForCraft fired: TS removed amount=%s'.[$amount]" context="false" filter="scripts"/>
            <do_if value="$amount == 10">
              <signal_cue_instantly cue="AwardXP" param="'weapon'"/>
            </do_if>
            <do_elseif value="$amount == 11">
              <signal_cue_instantly cue="AwardXP" param="'engine'"/>
            </do_elseif>
            <do_elseif value="$amount == 12">
              <signal_cue_instantly cue="AwardXP" param="'hull'"/>
            </do_elseif>
            <do_elseif value="$amount == 13">
              <signal_cue_instantly cue="AwardXP" param="'shield'"/>
            </do_elseif>
            <do_else>
              <debug_text text="'MOD: VolatileMods -- TS amount %s does not match any volatile category, ignoring.'.[$amount]" context="false" filter="scripts"/>
            </do_else>
          </actions>
        </cue>

        <!-- Award XP to a category and handle level-up. Param: category string. -->
        <cue name="AwardXP" instantiate="true">
          <conditions>
            <event_cue_signalled/>
          </conditions>
          <actions>
            <set_value name="$cat" exact="event.param"/>

            <!-- Pull current level/xp for the category using dynamic key. -->
            <set_value name="$curLvl" exact="global.$VolatileMods.$Level.{{'$' + $cat}}"/>
            <set_value name="$curXP"  exact="global.$VolatileMods.$XP.{{'$' + $cat}}"/>

            <!-- 1 Craft = 1 Level Up -->
            <set_value name="$gain" exact="1"/>
            <set_value name="$newXP" exact="$curXP + $gain"/>

            <debug_text text="'MOD: VolatileMods -- AwardXP: cat=%s curLvl=%s curXP=%s gain=%s newXP=%s'.[$cat, $curLvl, $curXP, $gain, $newXP]" context="false" filter="scripts"/>

            <!-- Target XP is 1 so every craft instantly triggers a level up -->
            <set_value name="$threshold" exact="1"/>

            <do_if value="$curLvl ge 40">
              <!-- Max level: cap XP at threshold (display-only). -->
              <set_value name="global.$VolatileMods.$XP.{{'$' + $cat}}" exact="$threshold"/>
              <do_if value="global.$VolatileMods.$CraftXPNotify">
                <show_notification text="[
                    'Volatile Mods',
                    '%s craft: MAX LEVEL reached (lv40).'.[$cat]
                  ]" timeout="3s" priority="2"/>
              </do_if>
            </do_if>
            <do_elseif value="$newXP ge $threshold">
              <!-- Level up! Carry over excess XP to the new level bar. -->
              <set_value name="$excess"  exact="0"/>
              <set_value name="$nextLvl" exact="$curLvl + 1"/>
              <set_value name="global.$VolatileMods.$Level.{{'$' + $cat}}" exact="$nextLvl"/>
              <set_value name="global.$VolatileMods.$XP.{{'$' + $cat}}"    exact="$excess"/>

              <!-- Grant blueprint for the new level. Wares list is 1-based:
                   index N+1 = lvN. Lower-level blueprints stay granted
                   (X4 MD has no remove_blueprints action). -->
              <add_blueprints wares="[global.$VolatileMods.$Wares.{{'$' + $cat}}.{{$nextLvl + 1}}]"/>

              <show_notification text="[
                  'Volatile Mods -- Level Up!',
                  '%s Basic: lv%s -> lv%s unlocked.'.[$cat, $curLvl, $nextLvl]
                ]" timeout="5s" priority="3"/>
              <debug_text text="'MOD: VolatileMods -- LEVEL UP %s: lv%s -> lv%s (carry %s XP).'.[$cat, $curLvl, $nextLvl, $excess]" context="false" filter="scripts"/>
            </do_elseif>
            <do_else>
              <!-- Normal gain. -->
              <set_value name="global.$VolatileMods.$XP.{{'$' + $cat}}" exact="$newXP"/>
              <do_if value="global.$VolatileMods.$CraftXPNotify">
                <show_notification text="[
                    'Volatile Mods',
                    '%s Basic craft: +%s XP (%s / %s to lv%s).'.[$cat, $gain, $newXP, $threshold, $curLvl + 1]
                  ]" timeout="3s" priority="2"/>
              </do_if>
            </do_else>
          </actions>
        </cue>

        <!-- Simple_Menu_API registration. -->
        <cue name="RegisterOptions" instantiate="true">
          <conditions>
            <event_cue_signalled cue="md.Simple_Menu_API.Reloaded"/>
          </conditions>
          <actions>
            <signal_cue_instantly cue="md.Simple_Menu_API.Register_Options_Menu" param="table[
                $id = 'volatile_mods_options',
                $columns = 3,
                $title = 'Volatile Mods',
                $onOpen = BuildOptions
              ]"/>
          </actions>
        </cue>

        <cue name="BuildOptions" instantiate="true">
          <conditions>
            <event_cue_signalled/>
          </conditions>
          <actions>
            <!-- Header -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 3,
                $text = 'Volatile Mods - Settings',
                $titleText = true
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 3,
                $text = 'Buy packs at equipment docks. Every stat rolls uniformly in the level range; permanent once applied. Per-category TS craft cost: Shield 13, Engine 11, Weapon 10, Hull 12. CRAFT packs to earn category XP and unlock higher levels.'
              ]"/>

            <!-- ======================== XP progression ======================== -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 3,
                $text = '-- Crafting XP progression --'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[ $col = 1, $text = 'Category' ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[ $col = 2, $text = 'Level' ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[ $col = 3, $text = 'XP progress' ]"/>

            <!-- Shield row -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[ $col = 1, $text = 'Shield' ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 2,
                $text = 'lv%s'.[global.$VolatileMods.$Level.$shield]
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 3,
                $text = if global.$VolatileMods.$Level.$shield ge 40 then 'MAX' else '%s / %s  (to lv%s)'.[10 * global.$VolatileMods.$Level.$shield + 5 * global.$VolatileMods.$Level.$shield * (global.$VolatileMods.$Level.$shield - 1) / 2 + global.$VolatileMods.$XP.$shield, 10 * (global.$VolatileMods.$Level.$shield + 1) + 5 * (global.$VolatileMods.$Level.$shield + 1) * global.$VolatileMods.$Level.$shield / 2, global.$VolatileMods.$Level.$shield + 1]
              ]"/>

            <!-- Engine row -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[ $col = 1, $text = 'Engine' ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 2,
                $text = 'lv%s'.[global.$VolatileMods.$Level.$engine]
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 3,
                $text = if global.$VolatileMods.$Level.$engine ge 40 then 'MAX' else '%s / %s  (to lv%s)'.[10 * global.$VolatileMods.$Level.$engine + 5 * global.$VolatileMods.$Level.$engine * (global.$VolatileMods.$Level.$engine - 1) / 2 + global.$VolatileMods.$XP.$engine, 10 * (global.$VolatileMods.$Level.$engine + 1) + 5 * (global.$VolatileMods.$Level.$engine + 1) * global.$VolatileMods.$Level.$engine / 2, global.$VolatileMods.$Level.$engine + 1]
              ]"/>

            <!-- Weapon row -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[ $col = 1, $text = 'Weapon' ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 2,
                $text = 'lv%s'.[global.$VolatileMods.$Level.$weapon]
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 3,
                $text = if global.$VolatileMods.$Level.$weapon ge 40 then 'MAX' else '%s / %s  (to lv%s)'.[10 * global.$VolatileMods.$Level.$weapon + 5 * global.$VolatileMods.$Level.$weapon * (global.$VolatileMods.$Level.$weapon - 1) / 2 + global.$VolatileMods.$XP.$weapon, 10 * (global.$VolatileMods.$Level.$weapon + 1) + 5 * (global.$VolatileMods.$Level.$weapon + 1) * global.$VolatileMods.$Level.$weapon / 2, global.$VolatileMods.$Level.$weapon + 1]
              ]"/>

            <!-- Hull row -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[ $col = 1, $text = 'Hull' ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 2,
                $text = 'lv%s'.[global.$VolatileMods.$Level.$hull]
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 3,
                $text = if global.$VolatileMods.$Level.$hull ge 40 then 'MAX' else '%s / %s  (to lv%s)'.[10 * global.$VolatileMods.$Level.$hull + 5 * global.$VolatileMods.$Level.$hull * (global.$VolatileMods.$Level.$hull - 1) / 2 + global.$VolatileMods.$XP.$hull, 10 * (global.$VolatileMods.$Level.$hull + 1) + 5 * (global.$VolatileMods.$Level.$hull + 1) * global.$VolatileMods.$Level.$hull / 2, global.$VolatileMods.$Level.$hull + 1]
              ]"/>

            <!-- Craft XP notify toggle -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 2,
                $text = 'Debug craft XP notifications',
                $mouseOverText = 'When ON, shows a ticker on each craft with the XP gained and progress toward the next level.'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Button" param="table[
                $col = 3,
                $onClick = Toggle_CraftXPNotify,
                $text = table[
                  $text = if global.$VolatileMods.$CraftXPNotify then 'ON' else 'OFF',
                  $color = if global.$VolatileMods.$CraftXPNotify then 'Color.text_success' else 'Color.text_failure',
                  $halign = 'center'
                ]
              ]"/>

            <!-- ======================== Tuning Software drops ======================== -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 3,
                $text = '-- Tuning Software drops (per ship size) --'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 3,
                $text = 'Yield value: 100 = guaranteed 1 TS, 200 = guaranteed 2, 50 = 50%% chance of 1, 150 = guaranteed 1 + 50%% chance of a 2nd. 0 = off.'
              ]"/>

            <!-- S -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 2,
                $text = 'S ship drop yield',
                $mouseOverText = 'TS yield when you destroy an S-class ship. Default 10%.'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Slider" param="table[
                $col = 3,
                $onSliderCellConfirm = Set_TSDropS,
                $min = 0, $minSelect = 0,
                $max = 300, $maxSelect = 300,
                $exceedMaxValue = false,
                $start = global.$VolatileMods.$TSDropS,
                $step = 1,
                $suffix = '%'
              ]"/>

            <!-- M -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 2,
                $text = 'M ship drop yield',
                $mouseOverText = 'TS yield when you destroy an M-class ship. Default 50%.'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Slider" param="table[
                $col = 3,
                $onSliderCellConfirm = Set_TSDropM,
                $min = 0, $minSelect = 0,
                $max = 300, $maxSelect = 300,
                $exceedMaxValue = false,
                $start = global.$VolatileMods.$TSDropM,
                $step = 1,
                $suffix = '%'
              ]"/>

            <!-- L -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 2,
                $text = 'L ship drop yield',
                $mouseOverText = 'TS yield when you destroy an L-class ship. Default 100% (= guaranteed 1 TS).'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Slider" param="table[
                $col = 3,
                $onSliderCellConfirm = Set_TSDropL,
                $min = 0, $minSelect = 0,
                $max = 300, $maxSelect = 300,
                $exceedMaxValue = false,
                $start = global.$VolatileMods.$TSDropL,
                $step = 1,
                $suffix = '%'
              ]"/>

            <!-- XL -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 2,
                $text = 'XL ship drop yield',
                $mouseOverText = 'TS yield when you destroy an XL-class ship. Default 200% (= guaranteed 2 TS).'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Slider" param="table[
                $col = 3,
                $onSliderCellConfirm = Set_TSDropXL,
                $min = 0, $minSelect = 0,
                $max = 300, $maxSelect = 300,
                $exceedMaxValue = false,
                $start = global.$VolatileMods.$TSDropXL,
                $step = 1,
                $suffix = '%'
              ]"/>

            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 2,
                $text = 'Tuning Software in inventory'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 3,
                $text = '%s'.[player.entity.inventory.{{ware.modpart_tuningsoftware}}.count]
              ]"/>

            <!-- Debug toggle for drop notifications -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 2,
                $text = 'Debug drop notifications',
                $mouseOverText = 'When ON, shows a ticker on every player kill with the roll value and whether a Tuning Software dropped.'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Button" param="table[
                $col = 3,
                $onClick = Toggle_Debug,
                $text = table[
                  $text = if global.$VolatileMods.$Debug then 'ON' else 'OFF',
                  $color = if global.$VolatileMods.$Debug then 'Color.text_success' else 'Color.text_failure',
                  $halign = 'center'
                ]
              ]"/>

            <!-- ======================== Emergency ======================== -->
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 3,
                $text = '-- Emergency --'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Add_Row"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Text" param="table[
                $col = 1, $colSpan = 2,
                $text = 'Re-grant all earned blueprints',
                $mouseOverText = 'Safety net. Re-grants lv0..currentLevel blueprints for each category. Safe to click even if already granted.'
              ]"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Make_Button" param="table[
                $col = 3,
                $onClick = Manual_GrantBlueprints,
                $text = table[ $text = 'Grant', $halign = 'center' ]
              ]"/>
          </actions>
        </cue>

        <cue name="Toggle_Debug" instantiate="true">
          <conditions><event_cue_signalled/></conditions>
          <actions>
            <set_value name="global.$VolatileMods.$Debug" exact="not global.$VolatileMods.$Debug"/>
            <show_notification text="[
                'Volatile Mods',
                'Debug drop notifications: %s'.[if global.$VolatileMods.$Debug then 'ON' else 'OFF']
              ]" timeout="3s" priority="3"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Refresh_Menu"/>
          </actions>
        </cue>

        <cue name="Toggle_CraftXPNotify" instantiate="true">
          <conditions><event_cue_signalled/></conditions>
          <actions>
            <set_value name="global.$VolatileMods.$CraftXPNotify" exact="not global.$VolatileMods.$CraftXPNotify"/>
            <show_notification text="[
                'Volatile Mods',
                'Debug craft XP notifications: %s'.[if global.$VolatileMods.$CraftXPNotify then 'ON' else 'OFF']
              ]" timeout="3s" priority="3"/>
            <signal_cue_instantly cue="md.Simple_Menu_API.Refresh_Menu"/>
          </actions>
        </cue>

        <cue name="Set_TSDropS" instantiate="true">
          <conditions><event_cue_signalled/></conditions>
          <actions>
            <set_value name="global.$VolatileMods.$TSDropS" exact="event.param.$value"/>
          </actions>
        </cue>

        <cue name="Set_TSDropM" instantiate="true">
          <conditions><event_cue_signalled/></conditions>
          <actions>
            <set_value name="global.$VolatileMods.$TSDropM" exact="event.param.$value"/>
          </actions>
        </cue>

        <cue name="Set_TSDropL" instantiate="true">
          <conditions><event_cue_signalled/></conditions>
          <actions>
            <set_value name="global.$VolatileMods.$TSDropL" exact="event.param.$value"/>
          </actions>
        </cue>

        <cue name="Set_TSDropXL" instantiate="true">
          <conditions><event_cue_signalled/></conditions>
          <actions>
            <set_value name="global.$VolatileMods.$TSDropXL" exact="event.param.$value"/>
          </actions>
        </cue>

        <cue name="Manual_GrantBlueprints" instantiate="true">
          <conditions><event_cue_signalled/></conditions>
          <actions>
            <!-- Re-grant lv0..currentLevel for each category. Wares list is
                 1-based: index N+1 = lvN, so loop 1..currentLevel+1. -->
            <do_all exact="global.$VolatileMods.$Level.$shield + 1" counter="$i">
              <add_blueprints wares="[global.$VolatileMods.$Wares.$shield.{{$i}}]"/>
            </do_all>
            <do_all exact="global.$VolatileMods.$Level.$engine + 1" counter="$i">
              <add_blueprints wares="[global.$VolatileMods.$Wares.$engine.{{$i}}]"/>
            </do_all>
            <do_all exact="global.$VolatileMods.$Level.$weapon + 1" counter="$i">
              <add_blueprints wares="[global.$VolatileMods.$Wares.$weapon.{{$i}}]"/>
            </do_all>
            <do_all exact="global.$VolatileMods.$Level.$hull + 1" counter="$i">
              <add_blueprints wares="[global.$VolatileMods.$Wares.$hull.{{$i}}]"/>
            </do_all>
            <debug_text text="'MOD: VolatileMods -- Manual_GrantBlueprints: re-granted lv0..currentLevel for all 4 categories.'" context="false" filter="scripts"/>
            <show_notification text="[
                'Volatile Mods',
                'Re-granted lv0..currentLevel blueprints for Shield / Engine / Weapon / Hull.'
              ]" timeout="4s" priority="3"/>
          </actions>
        </cue>

      </cues>
    </cue>

  </cues>
</mdscript>
'''

def main():
    wares = gen_wares()
    mods  = gen_equipmentmods()
    md    = gen_md()

    with open(os.path.join(LIB_DIR, "wares.xml"), "w", encoding="utf-8") as f:
        f.write(wares)
    with open(os.path.join(LIB_DIR, "equipmentmods.xml"), "w", encoding="utf-8") as f:
        f.write(mods)
    with open(os.path.join(MD_DIR, "volatile_mods.xml"), "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote wares.xml ({len(wares.splitlines())} lines)")
    print(f"Wrote equipmentmods.xml ({len(mods.splitlines())} lines)")
    print(f"Wrote md/volatile_mods.xml ({len(md.splitlines())} lines)")

if __name__ == "__main__":
    main()
