import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ModuleNotFoundError:
    class _Env:
        metadata = {}

        def reset(self, seed=None, options=None):
            self._seed = seed
            return None

    class _Discrete:
        def __init__(self, n):
            self.n = n

    class _Box:
        def __init__(self, low, high, dtype=np.float32):
            self.low = np.array(low, dtype=dtype)
            self.high = np.array(high, dtype=dtype)
            self.dtype = dtype
            self.shape = self.low.shape

    class _SpacesModule:
        Box = _Box
        Discrete = _Discrete

    class _GymModule:
        Env = _Env

    gym = _GymModule()
    spaces = _SpacesModule()
