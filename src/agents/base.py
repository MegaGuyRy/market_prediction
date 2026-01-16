"""Agent Base Class."""


class Agent:
    """Base class for all agents."""
    
    def __init__(self, name, role_description):
        self.name = name
        self.role = role_description
        self.response_format = "json"
    
    def critique(self, proposal, context):
        """
        Critique a proposal.
        
        Returns: {
            'recommendation': 'APPROVE'|'VETO'|'REDUCE',
            'reasoning': str,
            'json_response': dict
        }
        """
        pass
    
    def _query_llm(self, prompt):
        """Query LLM for response."""
        pass
    
    def _parse_response(self, response):
        """Parse LLM response to JSON."""
        pass
