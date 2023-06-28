class Message:
    def __init__(self, op, time, console):
        self.operator = op
        self.shift_time = time
        self.console = console
    
    def __ne__(self, other): 
        if not isinstance(other, Message):
            return NotImplemented