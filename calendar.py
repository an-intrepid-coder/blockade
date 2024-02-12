from constants import *

class Calendar:
    def __init__(self):
        self.day = 1
        self.hour = 0
        self.minute = 0
        self.second = 0

    def copy(self):
        cal = Calendar()
        cal.day = self.day
        cal.hour = self.hour
        cal.minute = self.minute
        cal.second = self.minute
        return cal

    def get_eta_str(self, current_tu, target_tu, scale): 
        cal = self.copy()       
        for tu in range(current_tu, target_tu + 1):
            cal.advance(scale)
        string = cal.clock_string() 
        if scale == "campaign":
            return "{} on day {}".format(string, cal.day)
        return string

    def advance(self, scale):
        if scale == "campaign":
            self.minute += MINUTES_PER_TU_CAMPAIGN
        elif scale == "tactical":
            self.second += SECONDS_PER_TU_TACTICAL
        if self.second >= 60:
            self.second -= 60
            self.minute += 1
        if self.minute >= 60:
            self.minute -= 60
            self.hour += 1
        if self.hour >= 24:
            self.hour -= 24
            self.day += 1

    def clock_string(self, seconds=False):
        if self.hour > 9:
            hour = "{}".format(self.hour)
        else:
            hour = "0{}".format(self.hour)
        if self.minute > 9:
            minute = "{}".format(self.minute)
        else:
            minute = "0{}".format(self.minute)
        if self.second > 9:
            second = "{}".format(self.second)
        else:
            second = "0{}".format(self.second)
        if seconds:
            return "{}:{}:{}".format(hour, minute, second)
        else:
            return "{}:{}".format(hour, minute)

