#!/usr/bin/env python3
"""Exercise the actual modern AI against synthetic epochs, without radios."""
import copy
import io
from pathlib import Path
import sys
import tempfile
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from stable_baselines3 import A2C
from stable_baselines3.common.env_checker import check_env
from pwnagotchi import ai
from pwnagotchi.ai import featurizer
from pwnagotchi.ai.gym import Environment
from pwnagotchi.ai.train import AsyncTrainer


class Agent:
    def supported_channels(self):
        return [1, 6, 11]

    def is_training(self):
        return True

    def on_ai_policy(self, params):
        self.last_policy = params

    def on_ai_step(self):
        pass


class Epoch:
    def wait_for_epoch_data(self):
        state = {key: 0 for key in (
            'num_deauths', 'num_associations', 'num_handshakes',
            'inactive_for_epochs', 'active_for_epochs', 'missed_interactions', 'num_hops')}
        state.update(reward=0.0, duration_secs=1,
                     aps_histogram=np.zeros(featurizer.histogram_size, dtype=np.float32),
                     sta_histogram=np.zeros(featurizer.histogram_size, dtype=np.float32),
                     peers_histogram=np.zeros(featurizer.histogram_size, dtype=np.float32))
        return state


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='pwn-ai-test-') as folder:
        config = tomllib.loads((root / 'pwnagotchi/defaults.toml').read_text())
        config['ai']['path'] = str(Path(folder) / 'brain.nn')
        config['ai']['params']['verbose'] = 0
        original = copy.deepcopy(config)
        agent, epoch = Agent(), Epoch()
        env = Environment(agent, epoch)
        check_env(env, warn=True)
        other = Environment(agent, epoch)
        assert env.action_space.shape == other.action_space.shape, 'Channel parameters accumulated'
        model = ai.load(config, agent, epoch, from_disk=False)
        assert model is not False, 'AI failed to initialize'
        model.learn(total_timesteps=4)
        observation = model.env.reset()
        action, _ = model.predict(observation, deterministic=True)
        model.env.step(action)
        # Use the production saving method, including its atomic temporary file.
        trainer = object.__new__(AsyncTrainer)
        trainer._nn_path = config['ai']['path']
        trainer._model = model
        trainer._save_ai()
        trainer._backup_ai()
        assert Path(trainer._nn_path).is_file(), 'Training backup removed the live brain'
        assert Path(trainer._nn_path).read_bytes() == Path(trainer._nn_path + '.bak').read_bytes()
        loaded = ai.load(config, agent, epoch, from_disk=True)
        assert loaded is not False, 'AI failed to reload'
        after, _ = loaded.predict(observation, deterministic=True)
        np.testing.assert_array_equal(action, after)
        for key, tensor in model.policy.state_dict().items():
            np.testing.assert_array_equal(tensor.cpu().numpy(), loaded.policy.state_dict()[key].cpu().numpy())
        assert config == original, 'AI initialization mutated its input configuration'
        assert 'channels' in agent.last_policy
        model.env.close()
        loaded.env.close()
        env.close()
        other.close()
    print('PASS: Gymnasium API, isolated environments, AI training/inference, atomic saving and loading')


if __name__ == '__main__':
    main()
