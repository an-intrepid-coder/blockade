from alert_level import AlertLevel

# situational roll modifiers

# applies to situations where passive sonar is detecting a torpedo
noisy_torpedo_bonus_to_passive_sonar_detection = 3

# torpedos are much harder to spot than surface vessels, even though they can be
# seen near the surface sometimes. 
torpedo_is_relatively_hard_to_spot = -2 # tentative; maybe -1

# launching a torpedo is a relatively easy task, compared to other things the skill
# could be used for. But it does go wrong sometimes.
torpedo_launch_is_routine = 1

# if piloting a torpedo against a target who is ENGAGED, it's a little harder. 
def pilot_torpedo_against_engaged_target_is_challenging(alert_level) -> int:
    if alert_level == AlertLevel.ENGAGED: return 1
    return 0

# Evading a torpedo with maneuvers is a relatively challenging task under ideal conditions
# NOTE: may increase this one
torpedo_evasion_is_challenging = 1

