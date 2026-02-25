class MemoryManager:
    """
    Manages conversation history and short-term memory.
    """
    def __init__(self):
        self.history = []

    def add_message(self, message: str):
        self.history.append(message)
