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

# returns 0 if piloting against an ENGAGED opponent.
# otherwise, a huge bonus.
def pilot_torpedo_alert_mod(alert_level) -> int:
    if alert_level == AlertLevel.ENGAGED: return 0
    return -4

