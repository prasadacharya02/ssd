# ============================================================
# ENTROPY - DQN Model
# ai\dqn_model.py
#
# WHAT THIS IS:
# Deep Q-Network for ransomware detection.
#
# HOW DQN WORKS:
# - Takes a STATE (features about current file activity)
# - Outputs Q-VALUES (score for each possible action)
# - Picks action with HIGHEST Q-VALUE
# - Learns from REWARDS (correct=positive, wrong=negative)
#
# ACTIONS:
# 0 = IGNORE    (normal activity, do nothing)
# 1 = ALERT     (suspicious, notify admin)
# 2 = TERMINATE (kill the process)
# 3 = TERMINATE + QUARANTINE (full response)
# ============================================================

import os
import sys
import json
import random
import tempfile
import numpy as np
from collections import deque

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# ============================================================
# NEURAL NETWORK
# The actual deep learning model inside the DQN.
# ============================================================

class QNetwork(nn.Module):
    """
    The neural network that approximates Q-values.

    INPUT:  State vector (10 features)
    OUTPUT: Q-value for each action (4 values)

    ARCHITECTURE:
    ─────────────
    Input (10)
        ↓
    Dense (128) + ReLU + Dropout
        ↓
    Dense (64)  + ReLU + Dropout
        ↓
    Dense (32)  + ReLU
        ↓
    Output (4)  - one Q-value per action
    """

    def __init__(self, state_size: int, action_size: int):
        super(QNetwork, self).__init__()

        self.state_size  = state_size
        self.action_size = action_size

        # Define layers
        self.fc1     = nn.Linear(state_size, 128)
        self.fc2     = nn.Linear(128, 64)
        self.fc3     = nn.Linear(64, 32)
        self.output  = nn.Linear(32, action_size)

        # Dropout for regularization
        self.dropout = nn.Dropout(p=0.2)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize weights using Xavier initialization."""
        for layer in [self.fc1, self.fc2, self.fc3, self.output]:
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, x):
        """
        Forward pass through the network.

        Args:
            x: State tensor of shape (batch_size, state_size)

        Returns:
            Q-values tensor of shape (batch_size, action_size)
        """
        x = F.relu(self.fc1(x))
        x = self.dropout(x)

        x = F.relu(self.fc2(x))
        x = self.dropout(x)

        x = F.relu(self.fc3(x))

        # Output layer - no activation (raw Q-values)
        q_values = self.output(x)

        return q_values


# ============================================================
# EXPERIENCE REPLAY BUFFER
# Stores past experiences for training.
# Learning from random past experiences prevents overfitting.
# ============================================================

class ReplayBuffer:
    """
    Stores (state, action, reward, next_state, done) tuples.

    WHY WE NEED THIS:
    -----------------
    If we train only on the current experience, the model
    becomes biased toward recent events.

    By storing many past experiences and sampling randomly,
    the model learns from a diverse set of situations.

    This is called Experience Replay.
    """

    def __init__(self, capacity: int = 10000):
        self.buffer   = deque(maxlen=capacity)
        self.capacity = capacity

    def push(self, state, action, reward, next_state, done):
        """Add an experience to the buffer."""
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        """
        Sample a random batch of experiences.

        Returns:
            Tuple of (states, actions, rewards, next_states, dones)
            Each as a numpy array.
        """
        batch = random.sample(self.buffer, batch_size)

        states      = np.array([e[0] for e in batch], dtype=np.float32)
        actions     = np.array([e[1] for e in batch], dtype=np.int64)
        rewards     = np.array([e[2] for e in batch], dtype=np.float32)
        next_states = np.array([e[3] for e in batch], dtype=np.float32)
        dones       = np.array([e[4] for e in batch], dtype=np.float32)

        return states, actions, rewards, next_states, dones

    def __len__(self):
        return len(self.buffer)

    def is_ready(self, batch_size: int) -> bool:
        """Check if we have enough samples to train."""
        return len(self.buffer) >= batch_size


# ============================================================
# FEATURE EXTRACTOR
# Converts raw event data into a normalized feature vector.
# The DQN needs consistent numerical input.
# ============================================================

class FeatureExtractor:
    """
    Converts pipeline events into DQN state vectors.

    FEATURES (10 total):
    ────────────────────
    0: entropy_score      (0.0 - 8.0, normalized to 0-1)
    1: entropy_delta      (-8 to +8, normalized to 0-1)
    2: files_per_sec      (0 - 50+, normalized to 0-1)
    3: ext_changed        (0 or 1)
    4: process_age_sec    (0 - 3600+, normalized to 0-1)
    5: is_signed          (0 or 1)
    6: files_affected     (0 - 200+, normalized to 0-1)
    7: avg_entropy_hist   (0.0 - 8.0, normalized to 0-1)
    8: is_known_process   (0 or 1)
    9: time_hour          (0 - 23, normalized to 0-1)
    """

    # Normalization ranges for each feature
    FEATURE_RANGES = {
        'entropy_score'   : (0.0, 8.0),
        'entropy_delta'   : (-8.0, 8.0),
        'files_per_sec'   : (0.0, 50.0),
        'ext_changed'     : (0.0, 1.0),
        'process_age_sec' : (0.0, 3600.0),
        'is_signed'       : (0.0, 1.0),
        'files_affected'  : (0.0, 200.0),
        'avg_entropy_hist': (0.0, 8.0),
        'is_known_process': (0.0, 1.0),
        'time_hour'       : (0.0, 23.0),
    }

    def __init__(self):
        self.entropy_history = {}    # track per-process entropy

    def extract(self, event: dict) -> np.ndarray:
        """
        Extract and normalize features from a pipeline event.

        Args:
            event: Analyzed event from the pipeline

        Returns:
            Normalized feature vector (numpy array, shape: (10,))
        """

        # Get raw values
        entropy_score = float(event.get('entropy_overall') or 0.0)
        entropy_delta = float(event.get('entropy_delta') or 0.0)
        files_per_sec = float(event.get('events_per_sec') or 0.0)
        ext_changed   = float(1 if event.get('ext_changed') else 0)

        # Process info
        process       = event.get('process') or {}
        process_age   = float(process.get('age_seconds') or 300.0)
        is_signed     = float(0)    # simplified: assume unsigned if unknown

        # Check if process is in whitelist (known/signed)
        proc_name = (process.get('name') or '').lower()
        if proc_name in [p.lower() for p in config.WHITELISTED_PROCESSES]:
            is_signed     = 1.0
            is_known      = 1.0
        else:
            is_known      = 0.0

        # Files affected count
        files_affected = float(event.get('events_in_window') or 1)

        # Historical entropy average for this process
        pid = str(process.get('pid') or 'unknown')
        if pid not in self.entropy_history:
            self.entropy_history[pid] = []
        self.entropy_history[pid].append(entropy_score)

        # Keep only last 20 readings
        if len(self.entropy_history[pid]) > 20:
            self.entropy_history[pid].pop(0)

        avg_entropy = np.mean(self.entropy_history[pid])

        # Time of day
        from datetime import datetime
        time_hour = float(datetime.now().hour)

        # Build raw feature vector
        raw_features = np.array([
            entropy_score,    # feature 0
            entropy_delta,    # feature 1
            files_per_sec,    # feature 2
            ext_changed,      # feature 3
            process_age,      # feature 4
            is_signed,        # feature 5
            files_affected,   # feature 6
            avg_entropy,      # feature 7
            is_known,         # feature 8
            time_hour,        # feature 9
        ], dtype=np.float32)

        # Normalize each feature to [0, 1]
        normalized = self._normalize(raw_features)

        return normalized

    def extract_from_dict(self, data: dict) -> np.ndarray:
        """
        Extract features from a training data dictionary.
        Used during model training (not live events).
        """
        raw_features = np.array([
            float(data.get('entropy_score',    0.0)),
            float(data.get('entropy_delta',    0.0)),
            float(data.get('files_per_sec',    0.0)),
            float(data.get('ext_changed',      0)),
            float(data.get('process_age_sec',  300.0)),
            float(data.get('is_signed',        0)),
            float(data.get('files_affected',   1)),
            float(data.get('avg_entropy_hist', 0.0)),
            float(data.get('is_known_process', 0)),
            float(data.get('time_hour',        12)),
        ], dtype=np.float32)

        return self._normalize(raw_features)

    def _normalize(self, features: np.ndarray) -> np.ndarray:
        """Normalize features to [0, 1] range."""
        ranges = list(self.FEATURE_RANGES.values())
        normalized = np.zeros_like(features)

        for i, (min_val, max_val) in enumerate(ranges):
            if max_val > min_val:
                val = (features[i] - min_val) / (max_val - min_val)
                normalized[i] = np.clip(val, 0.0, 1.0)
            else:
                normalized[i] = 0.0

        return normalized


# ============================================================
# DQN AGENT
# The main AI agent that makes decisions.
# ============================================================

class DQNAgent:
    """
    Deep Q-Network Agent for ransomware detection.

    DECISION PROCESS:
    ─────────────────
    1. Receive state (feature vector)
    2. Query Q-network for action Q-values
    3. Select action with highest Q-value
    4. Receive reward from environment
    5. Store experience in replay buffer
    6. Periodically train on random batch from buffer
    7. Repeat

    EXPLORATION vs EXPLOITATION:
    ────────────────────────────
    Early training: Random actions (explore)
    Later training: Best known action (exploit)
    Controlled by epsilon (starts high, decays over time)
    """

    def __init__(self,
                 state_size  : int = None,
                 action_size : int = None):

        self.state_size  = state_size  or config.STATE_SIZE
        self.action_size = action_size or config.ACTION_SIZE

        # Hyperparameters
        self.gamma         = config.GAMMA
        self.epsilon       = config.EPSILON_START
        self.epsilon_min   = config.EPSILON_END
        self.epsilon_decay = config.EPSILON_DECAY
        self.batch_size    = config.BATCH_SIZE
        self.lr            = config.LEARNING_RATE

        # Device (CPU or GPU)
        self.device = torch.device(
            'cuda' if torch.cuda.is_available() else 'cpu'
        )

        # Main network (trained every step)
        self.q_network = QNetwork(
            self.state_size, self.action_size
        ).to(self.device)

        # Target network (updated periodically for stability)
        self.target_network = QNetwork(
            self.state_size, self.action_size
        ).to(self.device)

        # Copy weights from main to target
        self.target_network.load_state_dict(
            self.q_network.state_dict()
        )
        self.target_network.eval()

        # Optimizer
        self.optimizer = optim.Adam(
            self.q_network.parameters(),
            lr=self.lr
        )

        # Replay buffer
        self.memory = ReplayBuffer(capacity=config.MEMORY_SIZE)

        # Feature extractor
        self.feature_extractor = FeatureExtractor()

        # Training stats
        self.training_step = 0
        self.episode       = 0
        self.losses        = []

        # Model save path
        self.model_path = os.path.join(
            config.AI_DIR, 'dqn_weights.pth'
        )

    # ── Action Selection ──────────────────────────────────

    def select_action(self, state: np.ndarray,
                      training: bool = False) -> int:
        """
        Select an action given the current state.

        During training: epsilon-greedy (sometimes random)
        During inference: always best action

        Args:
            state:    Feature vector (numpy array)
            training: If True, use epsilon-greedy exploration

        Returns:
            Action index (0, 1, 2, or 3)
        """

        # Exploration: random action
        if training and random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)

        # Exploitation: best known action
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(
            self.device
        )

        self.q_network.eval()
        with torch.no_grad():
            q_values = self.q_network(state_tensor)

        self.q_network.train()

        return q_values.argmax().item()

    def get_q_values(self, state: np.ndarray) -> np.ndarray:
        """
        Get Q-values for all actions given a state.
        Used for explainability (XAI).
        """
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(
            self.device
        )
        self.q_network.eval()
        with torch.no_grad():
            q_values = self.q_network(state_tensor)

        return q_values.cpu().numpy()[0]

    def decide(self, event: dict) -> dict:
        """
        Main decision function.
        Called by the pipeline with a live event.

        Returns a decision dictionary with:
        - action (int): 0-3
        - action_name (str): human readable
        - confidence (float): 0-1
        - q_values (list): raw Q-values
        - explanation (str): why this decision
        """

        # Extract features from event
        state = self.feature_extractor.extract(event)

        # Get Q-values
        q_values = self.get_q_values(state)

        # Select best action
        action = int(np.argmax(q_values))

        # Calculate confidence
        # (how much better is best action vs average)
        exp_q     = np.exp(q_values - np.max(q_values))
        softmax   = exp_q / exp_q.sum()
        confidence = float(softmax[action])

        # Action names
        action_names = {
            config.ACTION_IGNORE              : 'IGNORE',
            config.ACTION_ALERT               : 'ALERT',
            config.ACTION_TERMINATE           : 'TERMINATE',
            config.ACTION_TERMINATE_QUARANTINE: 'TERMINATE_AND_QUARANTINE',
        }

        action_name = action_names.get(action, 'UNKNOWN')

        # Build explanation
        explanation = self._explain_decision(
            state, action, q_values, event
        )

        return {
            'action'     : action,
            'action_name': action_name,
            'confidence' : round(confidence, 4),
            'q_values'   : q_values.tolist(),
            'state'      : state.tolist(),
            'explanation': explanation,
        }

    def _explain_decision(self, state, action,
                          q_values, event) -> str:
        """
        Generate a human-readable explanation.
        This is the XAI (Explainable AI) component.
        """
        parts = []

        entropy = event.get('entropy_overall') or 0
        delta   = event.get('entropy_delta') or 0
        speed   = event.get('events_per_sec') or 0
        score   = event.get('threat_score') or 0

        if entropy >= 7.5:
            parts.append(f"High entropy ({entropy:.2f})")
        if abs(delta) >= 2.0:
            parts.append(f"Large entropy change ({delta:+.2f})")
        if speed >= config.FILES_PER_SECOND_THRESHOLD:
            parts.append(f"High speed ({speed:.1f}/sec)")
        if event.get('ext_changed'):
            parts.append("File extension changed")

        if not parts:
            parts.append("Normal activity pattern")

        reason = ", ".join(parts)

        action_names = ['IGNORE', 'ALERT',
                       'TERMINATE', 'TERMINATE+QUARANTINE']
        action_str   = action_names[action]

        return (f"Decision: {action_str} | "
                f"Threat score: {score:.0f}/100 | "
                f"Reasons: {reason}")

    # ── Training ──────────────────────────────────────────

    def store_experience(self, state, action, reward,
                         next_state, done):
        """Store an experience in replay buffer."""
        self.memory.push(state, action, reward, next_state, done)

    def train_step(self) -> float:
        """
        Perform one training step.

        1. Sample random batch from replay buffer
        2. Calculate target Q-values using Bellman equation
        3. Calculate loss (prediction vs target)
        4. Backpropagate and update weights

        Returns:
            Loss value (float)
        """

        if not self.memory.is_ready(self.batch_size):
            return 0.0

        # Sample batch
        states, actions, rewards, next_states, dones = \
            self.memory.sample(self.batch_size)

        # Convert to tensors
        states_t      = torch.FloatTensor(states).to(self.device)
        actions_t     = torch.LongTensor(actions).to(self.device)
        rewards_t     = torch.FloatTensor(rewards).to(self.device)
        next_states_t = torch.FloatTensor(next_states).to(self.device)
        dones_t       = torch.FloatTensor(dones).to(self.device)

        # Current Q-values
        current_q = self.q_network(states_t).gather(
            1, actions_t.unsqueeze(1)
        ).squeeze(1)

        # Target Q-values (Bellman equation)
        with torch.no_grad():
            next_q      = self.target_network(next_states_t).max(1)[0]
            target_q    = rewards_t + self.gamma * next_q * (1 - dones_t)

        # Loss
        loss = F.smooth_l1_loss(current_q, target_q)

        # Optimize
        self.optimizer.zero_grad()
        loss.backward()

        # Clip gradients (stability)
        torch.nn.utils.clip_grad_norm_(
            self.q_network.parameters(), 1.0
        )

        self.optimizer.step()

        # Track loss
        loss_val = loss.item()
        self.losses.append(loss_val)

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        self.training_step += 1

        # Update target network periodically
        if self.training_step % config.TARGET_UPDATE == 0:
            self.target_network.load_state_dict(
                self.q_network.state_dict()
            )

        return loss_val

    # ── Save/Load ─────────────────────────────────────────

    def save(self, path: str = None):
        """Atomically save a self-describing model checkpoint."""
        path = path or self.model_path
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        checkpoint = {
            'checkpoint_version'   : 1,
            'q_network_state'     : self.q_network.state_dict(),
            'target_network_state': self.target_network.state_dict(),
            'optimizer_state'     : self.optimizer.state_dict(),
            'epsilon'             : float(self.epsilon),
            'training_step'       : int(self.training_step),
            'episode'             : int(self.episode),
            'state_size'          : self.state_size,
            'action_size'         : self.action_size,
        }

        # Never leave a partially written checkpoint that could be loaded on
        # the next startup. Replace is atomic on the same filesystem.
        fd, temporary_path = tempfile.mkstemp(
            prefix=".dqn-", suffix=".pth", dir=directory
        )
        os.close(fd)
        try:
            torch.save(checkpoint, temporary_path)
            os.replace(temporary_path, path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

        print(f"[DQN] Model saved: {path}")

    def _validate_checkpoint(self, checkpoint: dict) -> bool:
        """Validate checkpoint structure before mutating the live model."""
        required = {
            'q_network_state', 'target_network_state', 'optimizer_state',
            'epsilon', 'training_step', 'state_size', 'action_size',
        }
        if not isinstance(checkpoint, dict) or not required <= checkpoint.keys():
            return False
        if checkpoint.get('state_size') != self.state_size:
            return False
        if checkpoint.get('action_size') != self.action_size:
            return False
        if not 0.0 <= float(checkpoint['epsilon']) <= 1.0:
            return False
        if int(checkpoint['training_step']) < 0:
            return False
        return True

    def load(self, path: str = None) -> bool:
        """Safely load a compatible checkpoint; return False on any failure."""
        path = path or self.model_path
        if not os.path.exists(path):
            print(f"[DQN] No saved model at: {path}")
            return False

        try:
            try:
                checkpoint = torch.load(
                    path, map_location=self.device, weights_only=True
                )
            except TypeError:
                # Compatibility with older PyTorch versions. Checkpoints must
                # still come from a trusted local training run.
                checkpoint = torch.load(path, map_location=self.device)
            if not self._validate_checkpoint(checkpoint):
                raise ValueError("incompatible or malformed checkpoint")

            # Load into temporary state first so a bad checkpoint does not
            # leave the active network half-updated.
            q_state = checkpoint['q_network_state']
            target_state = checkpoint['target_network_state']
            self.q_network.load_state_dict(q_state, strict=True)
            self.target_network.load_state_dict(target_state, strict=True)
            self.optimizer.load_state_dict(checkpoint['optimizer_state'])
            self.epsilon = float(checkpoint['epsilon'])
            self.training_step = int(checkpoint['training_step'])
            self.episode = int(checkpoint.get('episode', 0))
        except Exception as exc:
            print(f"[DQN] Model rejected: {exc}")
            return False

        print(f"[DQN] Model loaded: {path}")
        print(f"[DQN] Training steps: {self.training_step}")
        print(f"[DQN] Epsilon: {self.epsilon:.4f}")
        return True

    def get_stats(self) -> dict:
        """Get training statistics."""
        recent_loss = (
            np.mean(self.losses[-100:])
            if len(self.losses) >= 100
            else np.mean(self.losses) if self.losses
            else 0.0
        )

        return {
            'training_steps' : self.training_step,
            'episode'        : self.episode,
            'epsilon'        : round(self.epsilon, 4),
            'memory_size'    : len(self.memory),
            'recent_loss'    : round(float(recent_loss), 6),
            'device'         : str(self.device),
        }