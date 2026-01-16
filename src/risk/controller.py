"""Risk Controller - main orchestrator of hard rules."""


class RiskController:
    """
    Final authority on trade approval.
    Pure code, no exceptions, cannot be overridden.
    """
    
    def evaluate_proposal(self, proposal, agent_recommendation, portfolio_state):
        """
        Evaluate proposal against all risk rules.
        
        Returns: {
            'approved': bool,
            'quantity': int,
            'stop_loss': float,
            'target': float,
            'rationale': str
        }
        """
        pass
    
    def _check_position_sizing(self, proposal, portfolio_state):
        """Check 0.5% risk per trade."""
        pass
    
    def _check_portfolio_constraints(self, proposal, portfolio_state):
        """Check max positions, exposure, single stock limits."""
        pass
    
    def _check_drawdown_limits(self, portfolio_state):
        """Check 2% soft / 3% hard drawdown limits."""
        pass
