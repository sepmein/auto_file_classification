END = "END"

class StateGraph:
    def __init__(self, state_type=None):
        self.state_type = state_type
        self.nodes = {}
        self.edges = {}
        self.entry = None

    def add_node(self, name, func):
        self.nodes[name] = func

    def set_entry_point(self, name):
        self.entry = name

    def add_edge(self, src, dest):
        self.edges.setdefault(src, []).append(dest)

    def compile(self):
        return self
