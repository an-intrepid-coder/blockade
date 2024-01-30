from random import randint

class Mission:
    def __init__(self):
        self.briefing_lines = []

class ConvoyAttack(Mission):
    def __init__(self):
        super().__init__()
        self.briefing_lines.extend([
            "___CONVOY ATTACK MISSION BRIEFING___",
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
        scale = randint(1, 2) # **
        if scale > 1: 
            self.briefing_lines.extend(["> This is a large convoy.", ""])
        subs = randint(1, 3) == 1 # **
        if subs:
            self.briefing_lines.extend(["> Enemy submarine escorts suspected.", ""])
        heavy_escort = randint(1, 6) == 1 # **
        if heavy_escort: 
            self.briefing_lines.extend([
                "> Powerful heavy escort ship suspected. This dangerous",
                "vessel has rocket-assisted torpedos with extended range",
                "and carries an ASW helicopter. Approach with caution.",
                "",
            ])
        offmap_asw = randint(1, 4) == 1 # **
        if offmap_asw: 
            self.briefing_lines.extend([
                "> Within range of land-based ASW patrol planes.",
                "They may drop lines of sonobuoys across the map.",
                "",
            ])
        neutral_freighters = randint(1, 3) == 1 # **
        if neutral_freighters: 
            self.briefing_lines.extend(["> Neutral shipping in the area.", ""])
        self.briefing_lines.append("<ESC to continue>")
        # NOTE: When campaign mode implemented soon, these chances be part of mission selection, and thethey will
        #       be contextual. Current setup for playing in the sandbox and testing mechanics.
        self.scale=scale
        self.freighters=True
        self.escorts=True
        self.subs=subs
        self.heavy_escort=heavy_escort
        self.offmap_asw=offmap_asw
        self.neutral_freighters=neutral_freighters

