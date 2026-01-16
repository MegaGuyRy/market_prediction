"""Bull Agent - best-case thesis evaluation."""


from .base import Agent


class BullAgent(Agent):
    """Present best-case thesis for a trade."""
    
    def __init__(self):
        super().__init__('bull', 'Best-case thesis evaluation')
    
    def critique(self, proposal, context):
        """
        Evaluate best-case scenario.
        
        Returns recommendation: APPROVE|VETO|REDUCE
        """
        pass
