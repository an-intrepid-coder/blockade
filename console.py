tags = ["rolls", "combat", "other"]

class Message:
    def __init__(self, msg, tag, turn):
        self.msg = msg
        self.tag = tag
        self.turn = turn

class Console: 
    def __init__(self):
        self.messages = [
            Message("______ROLLS______", "rolls", 0),
            Message("______COMBAT______", "combat", 0),
            Message("______MISC.______", "other", 0),
        ]

    def push(self, msg):
        self.messages.append(msg) 

