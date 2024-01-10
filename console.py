class Console: # TODO: a Message class for filtering and more complex things w/ metadata
    def __init__(self):
        self.messages = ["~-~-~-~-~-~ BLOCKADE ~-~-~-~-~-~"]

    def push(self, msg):
        self.messages.append(msg) 

