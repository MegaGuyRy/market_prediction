"""Bear Agent - counter-thesis and risks."""


from .base import Agent


class BearAgent(Agent):
    """Present counter-thesis and identify risks."""
    
    def __init__(self):
        super().__init__('bear', 'Counter-thesis and risk identification')
    
    def critique(self, proposal, context):
        """
        Evaluate counter-thesis and risks.
        
        Returns recommendation: APPROVE|VETO|REDUCE
        """
        pass
