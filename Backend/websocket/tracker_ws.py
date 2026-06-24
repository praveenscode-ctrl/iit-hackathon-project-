class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list] = {}

manager = ConnectionManager()
