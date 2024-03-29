from random import randint
from constants import *

class Mission:
    def __init__(self):
        self.briefing_lines = []
        self.freighters_sunk = 0
        self.escorts_sunk = 0
        self.subs_sunk = 0
        self.heavy_escorts_sunk = 0
        self.neutral_freighters_sunk = 0
        self.stealth_retained = True
        self.calculated = False

    def accomplished_something(self) -> bool:
        return self.freighters_sunk > 0 \
            or self.escorts_sunk > 0 \
            or self.subs_sunk > 0 \
            or self.heavy_escorts_sunk > 0 \
            or self.neutral_freighters_sunk > 0

class ConvoyAttack(Mission):
    def __init__(self, scale, subs, heavy_escort, offmap_asw, neutral_freighters):
        super().__init__()
        self.briefing_lines.extend([
            "___CONVOY ATTACK MISSION BRIEFING___", "",
            "You have positioned your attack submarine in front of an approaching enemy convoy,", 
            "loaded with valuable supplies. You are to investigate, destroy freighters if possible", 
            "and then evade the escorting forces. It is recommended that you await their approach", 
            "and then shadow them for awhile, until you have identified the disposition of their forces,", 
            "before making your attack. Take no chances! You are permitted to avoid the engagement if", 
            "it would seem unfavorable.",
            "",
            "___INTEL REPORT__",
            "",
        ])
        if scale > 1: 
            self.briefing_lines.extend(["> This is a large convoy.", ""])
        if subs:
            self.briefing_lines.extend(["> Enemy submarine escorts suspected.", ""])
        if heavy_escort: 
            self.briefing_lines.extend([
                "> Powerful heavy escort ship suspected. This dangerous",
                "vessel has rocket-assisted torpedos with extended range",
                "and carries an ASW helicopter. Approach with caution.",
                "",
            ])
        if offmap_asw: 
            self.briefing_lines.extend([
                "> Within range of land-based ASW patrol planes.",
                "They may drop lines of sonobuoys across the map.",
                "",
            ])
        if neutral_freighters: 
            self.briefing_lines.extend(["> Neutral shipping in the area.", ""])
        self.briefing_lines.append("<ESC to continue (note: mission starts paused)>")
        self.scale = scale
        self.freighters = True
        self.escorts = True
        self.subs = subs
        self.heavy_escort = heavy_escort
        self.offmap_asw = offmap_asw
        self.neutral_freighters = neutral_freighters
        self.boss_present = self.heavy_escort # NOTE: more "bosses" in time
        self.diff_mod = subs > 0 or offmap_asw or neutral_freighters
        self.player_fate = "Mission Survived!"

    def assessment_lines(self, player_hp) -> list:
        score = self.calculate_score(player_hp)
        lines = [
            "{}".format(self.player_fate), "",
            "___MISSION SCORE__", ""
        ]
        if player_hp < PLAYER_HP:
            lines.append("Damage Taken: ({})".format((PLAYER_HP - player_hp) * SCORE_HP))
        lines.extend([
            "Freighters Sunk: {} (+{} each)".format(self.freighters_sunk, SCORE_FREIGHTER),
            "Small Escorts Sunk: {} (+{} each)".format(self.escorts_sunk, SCORE_SMALL_CONVOY_ESCORT)
        ])
        if self.subs:
            lines.append("Escort Subs Sunk: {} (+{} each)".format(self.subs_sunk, SCORE_ESCORT_SUB))
        if self.heavy_escort:
            lines.append("Heavy Escorts Sunk: {} (+{} each)".format(self.heavy_escorts_sunk, SCORE_BOSS))
        if self.neutral_freighters:
            lines.append("Neutral Freighters Sunk: {} ({} each)".format(self.neutral_freighters_sunk, \
                SCORE_NEUTRAL_FREIGHTER))
        if self.stealth_retained:
            lines.append("Retained Stealth: (+{})".format(SCORE_STEALTH_RETAINED))
        if self.boss_present:
            lines.append("Boss Present: (+{}/Freighter)".format(SCORE_BOSS_PRESENT))
        if self.diff_mod:
            lines.append("Bonus for Subs/ASW/Neutrals Present: (+{}/Freighter)".format(SCORE_DIFF_MOD))
        lines.extend(["", "Total: {}".format(score)])
        return lines

    def calculate_score(self, player_hp) -> int:
        score = (PLAYER_HP - player_hp) * SCORE_HP      
        for _ in range(self.freighters_sunk):
            score += SCORE_FREIGHTER
            if self.boss_present:
                score += SCORE_BOSS_PRESENT
            if self.diff_mod:
                score += SCORE_DIFF_MOD
        for _ in range(self.escorts_sunk):
            score += SCORE_SMALL_CONVOY_ESCORT
        for _ in range(self.subs_sunk):
            score += SCORE_ESCORT_SUB
        for _ in range(self.heavy_escorts_sunk):
            score += SCORE_BOSS
        for _ in range(self.neutral_freighters_sunk):
            score += SCORE_NEUTRAL_FREIGHTER
        if self.stealth_retained:
            score += SCORE_STEALTH_RETAINED
        return score

class AswPatrol(Mission):
    def __init__(self, scale, offmap_asw):
        super().__init__()
        self.briefing_lines.extend([
            "___ASW PATROL MISSION BRIEFING___", "",
            "You have been spotted by an enemy ASW patrol! They are aware of your position, and",
            "will be upon you soon. If you have missiles in stock then you may be able to make a",
            "pre-emptive strike, but your best bet is to make a run for it.",
            "",
            "___INTEL REPORT__",
            "",
        ])
        if offmap_asw: 
            self.briefing_lines.extend([
                "> Within range of land-based ASW patrol planes.",
                "They may drop lines of sonobuoys across the map.",
                "",
            ])
        self.briefing_lines.append("<ESC to continue (note: mission starts paused)>")
        self.scale = scale
        self.freighters = False
        self.escorts = True
        self.subs = False
        self.heavy_escort = False
        self.offmap_asw = offmap_asw
        self.neutral_freighters = False
        self.boss_present = False
        self.diff_mod = offmap_asw
        self.player_fate = "Mission Survived!"

    def assessment_lines(self, player_hp) -> list: 
        score = self.calculate_score(player_hp)
        lines = [
            "{}".format(self.player_fate), "",
            "___MISSION SCORE__", 
            ""
        ]
        if player_hp < PLAYER_HP:
            lines.append("Damage Taken: ({})".format((PLAYER_HP - player_hp) * SCORE_HP))
        lines.extend([
            "Small Escorts Sunk: {} (+{} each)".format(self.escorts_sunk, SCORE_SMALL_CONVOY_ESCORT)
        ])
        if player_hp > 0:
            lines.append("Survival Bonus: {}".format(SCORE_ASW_PATROL_SURVIVAL))
        if self.stealth_retained:
            lines.append("Retained Stealth: (+{})".format(SCORE_STEALTH_RETAINED))
        if self.diff_mod:
            lines.append("Bonus for ASW Planes Present: (+{})".format(SCORE_ASW_PATROL_WITH_PLANES))
        lines.extend(["", "Total: {}".format(score)])
        return lines

    def calculate_score(self, player_hp) -> int: 
        score = (PLAYER_HP - player_hp) * SCORE_HP      
        if self.diff_mod:
            score += SCORE_ASW_PATROL_WITH_PLANES
        for _ in range(self.escorts_sunk):
            score += SCORE_SMALL_CONVOY_ESCORT
        if self.stealth_retained:
            score += SCORE_STEALTH_RETAINED
        if player_hp > 0:
            score += SCORE_ASW_PATROL_SURVIVAL
        return score

