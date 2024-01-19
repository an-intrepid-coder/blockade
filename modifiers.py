from alert_level import AlertLevel

# situational roll modifiers

# applies to situations where passive sonar is detecting a torpedo
noisy_torpedo_bonus_to_passive_sonar_detection = 2

# returns 0 if piloting against an ENGAGED opponent.
# otherwise, a huge bonus.
def pilot_torpedo_alert_mod(alert_level) -> int:
    if alert_level == AlertLevel.ENGAGED: return 0
    return -4

# Returns a penalty to passive psonar detection if target is in fast mode
# and a bonus or penalty based on observer speed
def moving_psonar_mod(observer, target) -> int:
    mod = 0
    if observer.momentum == 0:
        mod += 2
    elif observer.speed_mode == "fast":
        mod += -2
    if target.momentum == 0:
        mod += -2
    elif target.speed_mode == "fast":
        mod += 2
    return mod

