class MissingData(Exception):
    def __init__(self, message="No Data Available"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message
