import logging
from tqdm import tqdm

import numpy as np


class Core(object):
    """
    Implements the functions to run a generic algorithm.
    """
    def __init__(self, agent, mdp, callbacks=None, max_dataset_size=np.inf):
        """
        Constructor.

        # Arguments
            agent (object): the agent moving according to a policy;
            mdp (object): the environment in which the agent moves;
            callbacks (list): list of callbacks to execute at the end of
                each iteration.
        """
        self.agent = agent
        self.mdp = mdp
        self.callbacks = callbacks if callbacks is not None else list()

        self.agent.initialize(self.mdp.get_info())

        self.logger = logging.getLogger('logger')

        self._state = self.mdp.reset()

        self._total_steps = 0
        self._episode_steps = 0

    def learn(self, n_iterations, how_many, n_fit_steps, iterate_over,
              render=False, quiet=False):
        """
        This function is used to learn a policy. An iteration of the loop
        consists in collecting a dataset and fitting the agent's Q-function
        approximator on that. Multiple iterations can be done in order to append
        new samples to the dataset using the newly learned policies. This
        function generalizes the learning procedure of online and batch
        algorithms.

        # Arguments
            n_iterations (int > 0): number of iterations;
            how_many (int > 0): number of samples or episodes to collect in a
                single iteration of the loop;
            n_fit_steps (int > 0): number of fitting steps of the learning
                algorithm;
            iterate_over (string): whether to collect samples or episodes in a
                single iteration of the loop;
            render (bool): whether to render the environment or not.
        """
        assert iterate_over == 'samples' or iterate_over == 'episodes'

        if iterate_over == 'samples':
            for self.iteration in tqdm(xrange(n_iterations), dynamic_ncols=True,
                                       disable=quiet, leave=False):

                self.logger.debug('Moving for %d samples...' % how_many)
                dataset = self._move_samples(how_many, render=render)

                self.logger.debug('Fitting for %d steps...' % n_fit_steps)
                self.agent.fit(dataset, n_fit_steps)

                for c in self.callbacks:
                    c(dataset)

                self._total_steps += 1
        else:
            for self.iteration in tqdm(xrange(n_iterations), dynamic_ncols=True,
                                       disable=quiet, leave=False):

                self.logger.debug('Moving for %d episodes...' % how_many)
                dataset = self._move_episodes(how_many, render=render)

                self.logger.debug('Fitting for %d steps...' % n_fit_steps)
                self.agent.fit(dataset, n_fit_steps)

                for c in self.callbacks:
                    c(dataset)

    def evaluate(self, how_many=1, iterate_over='episodes', initial_states=None,
                 render=False, quiet=False):
        """
        This function is used to evaluate the learned policy.

        # Arguments
            initial_states (np.array): the array of initial states from where to
                start the evaluation episodes. An evaluation episode is run for
                each state;
            render (bool): whether to render the environment or not.
        """
        dataset = list()
        if initial_states is not None:
            assert iterate_over == 'episodes'

            self.logger.info('Evaluating policy for %d episodes...' %
                             initial_states.shape[0])
            for i in tqdm(xrange(initial_states.shape[0]), dynamic_ncols=True,
                          disable=quiet, leave=False):
                self._state = self.mdp.reset(initial_states[i, :])
                dataset += self._move_episodes(1, render=render)
        else:
            self.logger.info('Evaluating policy for %d %s...' %
                             (how_many, iterate_over))
            if iterate_over == 'episodes':
                for _ in tqdm(xrange(how_many), dynamic_ncols=True,
                              disable=quiet, leave=False):
                    self._state = self.mdp.reset()
                    dataset += self._move_episodes(1, render=render)
            else:
                self._state = self.mdp.reset()
                for _ in tqdm(xrange(how_many), dynamic_ncols=True,
                              disable=quiet, leave=False):
                    dataset += self._move_samples(1, render=render)

        return dataset

    def _move_episodes(self, how_many, render=False):
        """
        Move the agent.

        # Arguments
            how_many (int > 0): number of samples or episodes to collect;
            collect (bool): whether to store the collected data or not;
            render (bool): whether to render the environment or not.

        # Returns
            The list of discounted rewards obtained in each episode.
        """
        i = 0
        dataset = list()
        self._episode_steps = 0
        while i < how_many:
            self.logger.debug('Starting in state: ' + str(self._state))
            while not self._step(dataset, render):
                continue
            self.logger.debug('Ended in state: ' + str(self._state))
            self._state = self.mdp.reset()
            self._episode_steps = 0
            i += 1

        return dataset

    def _move_samples(self, how_many, render=False):
        i = 0
        dataset = list()
        while i < how_many:
            if self._step(dataset, render):
                self._state = self.mdp.reset()
                self._episode_steps = 0
            i += 1

        return dataset

    def _step(self, dataset, render):
        """
        Single step.

        # Arguments
            collect (bool): whether to collect the sample or not.
            render (bool): whether to render or not.
        """
        action = self.agent.draw_action(self._state)
        next_state, reward, absorbing, _ = self.mdp.step(action)

        self._episode_steps += 1

        if render:
            self.mdp.render()

        last = not(self._episode_steps < self.mdp.horizon and not absorbing)
        sample = (self._state, action, reward, next_state, absorbing,
                  last)

        self.logger.debug(sample[:-1])

        dataset.append(sample)

        self._state = np.array(next_state)

        return last

    def reset(self):
        """
        Reset the stored dataset list.
        """
        self._state = self.mdp.reset()
        self._total_steps = 0
        self._episode_steps = 0
