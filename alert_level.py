from enum import Enum
from random import choice

class AlertLevel(Enum):  
    COMPLACENT = -2 
    RELAXED = -1
    PREPARED = 0
    ALERTED = 1
    ENGAGED = 2

def random_starting_alert_level() -> AlertLevel:
    return choice([AlertLevel.COMPLACENT, AlertLevel.RELAXED, AlertLevel.PREPARED])

