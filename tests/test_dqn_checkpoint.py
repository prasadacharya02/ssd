import importlib.util
import tempfile
from pathlib import Path
import unittest


TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None


@unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is optional")
class DQNCheckpointTests(unittest.TestCase):
    def test_malformed_checkpoint_is_rejected(self):
        from ai.dqn_model import DQNAgent
        import torch

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.pth"
            torch.save({"not": "a checkpoint"}, path)
            self.assertFalse(DQNAgent().load(str(path)))

    def test_save_and_load_round_trip(self):
        from ai.dqn_model import DQNAgent

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.pth"
            original = DQNAgent()
            original.training_step = 12
            original.save(str(path))
            restored = DQNAgent()
            self.assertTrue(restored.load(str(path)))
            self.assertEqual(restored.training_step, 12)


if __name__ == "__main__":
    unittest.main()
