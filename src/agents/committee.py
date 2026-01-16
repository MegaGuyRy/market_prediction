"""Committee Agent - synthesis of all agents."""


from .base import Agent


class CommitteeAgent(Agent):
    """Synthesize all agent critiques into final recommendation."""
    
    def __init__(self):
        super().__init__('committee', 'Consensus synthesis')
    
    def synthesize(self, analyst_critique, bull_critique, bear_critique, risk_critique):
        """
        Synthesize all agent critiques.
        
        Returns final recommendation: APPROVE|VETO|REDUCE
        """
        pass
