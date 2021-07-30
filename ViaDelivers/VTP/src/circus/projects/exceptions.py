class Error(Exception):
    pass

class IllegalActionError(Error):
    def __init__(self, msg):
        self.msg = msg
