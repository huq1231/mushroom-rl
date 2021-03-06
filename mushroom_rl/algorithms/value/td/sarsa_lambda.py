from mushroom_rl.algorithms.value.td import TD
from mushroom_rl.utils.eligibility_trace import EligibilityTrace
from mushroom_rl.utils.table import Table


class SARSALambda(TD):
    """
    The SARSA(lambda) algorithm for finite MDPs.

    """
    def __init__(self, mdp_info, policy, learning_rate, lambda_coeff,
                 trace='replacing'):
        """
        Constructor.

        Args:
            lambda_coeff (float): eligibility trace coefficient;
            trace (str, 'replacing'): type of eligibility trace to use.

        """
        self.Q = Table(mdp_info.size)
        self._lambda = lambda_coeff

        self.e = EligibilityTrace(self.Q.shape, trace)
        self._add_save_attr(
            Q='pickle',
            _lambda='numpy',
            e='pickle'
        )

        super().__init__(mdp_info, policy, self.Q, learning_rate)

    def _update(self, state, action, reward, next_state, absorbing):
        q_current = self.Q[state, action]

        self.next_action = self.draw_action(next_state)
        q_next = self.Q[next_state, self.next_action] if not absorbing else 0.

        delta = reward + self.mdp_info.gamma * q_next - q_current
        self.e.update(state, action)

        self.Q.table += self.alpha(state, action) * delta * self.e.table
        self.e.table *= self.mdp_info.gamma * self._lambda

    def episode_start(self):
        self.e.reset()

        super().episode_start()
