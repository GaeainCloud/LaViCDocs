from .state_schema import SharedState

class Orchestrator:
    def __init__(self):
        self.workflow = StateGraph(SharedState)
        # Add nodes and edges here
        
    def run(self, initial_state: SharedState):
        app = self.workflow.compile()
        return app.invoke(initial_state)
