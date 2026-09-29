# ============================================================
# ENTROPY - Ransomware Behavior Simulator
# data\ransomware_simulator.py
#
# WHAT THIS DOES:
# Safely simulates ransomware behavior for testing.
#
# IT DOES NOT:
# - Contain any real malware
# - Use any encryption keys
# - Spread or replicate
# - Touch files outside the test folder
#
# IT SIMULATES:
# - Rapid file modification (many files per second)
# - High entropy content (os.urandom = like encrypted)
# - File extension changes (.txt → .locked)
# - Bulk file operations
#
# PURPOSE:
# - Test that our detection system works
# - Generate training data for DQN
# - Demonstrate the system catching ransomware
# ============================================================

import os
import sys
import time
import random
import shutil
import logging
from datetime import datetime
from threading import Thread, Event

# Add parent folder to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ── Setup Logging ─────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [SIMULATOR] %(message)s",
    handlers= [logging.StreamHandler()]
)

import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

log = logging.getLogger("Simulator")


# ============================================================
# TEST ENVIRONMENT SETUP
# Creates realistic-looking files to simulate a real user's
# document folder before ransomware strikes.
# ============================================================

class TestEnvironment:
    """
    Creates and manages a test folder with realistic files.

    Simulates a user's Documents folder containing:
    - Text documents
    - Data files
    - Various file types

    All files are FAKE and contain dummy content.
    Nothing real is touched.
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.files    = []    # list of created file paths

    def setup(self, num_files: int = 30):
        """
        Create test files that look like real user files.

        Args:
            num_files: How many files to create
        """
        os.makedirs(self.base_dir, exist_ok=True)

        log.info(f"Creating {num_files} test files in:")
        log.info(f"  {self.base_dir}")

        # File templates to simulate real user files
# REPLACE WITH THIS:
        templates = [
            # (filename_pattern, content_generator, mode)

            # Normal text - LOW entropy (3-4)
            ("document_{}.txt",
             lambda i: (
                 f"Document Number {i}\n"
                 f"Author: Test User\n"
                 f"Date: 2024-01-{(i%28)+1:02d}\n\n"
                 f"This document contains normal readable text.\n"
                 f"The content is written in plain English.\n"
                 f"Normal documents have low entropy values.\n"
                 f"This is because text uses limited characters.\n\n"
                 f"Section 1: Introduction\n"
                 f"This section introduces the main topic.\n"
                 f"We discuss various aspects of the subject.\n\n"
                 f"Section 2: Details\n"
                 f"Here we provide more detailed information.\n"
                 f"The details are written in clear language.\n\n"
             ) * 20,
             'w'),

            # Report text - LOW entropy (3-4)
            ("report_{}.txt",
             lambda i: (
                 f"Monthly Report - Period {i}\n"
                 f"Department: Operations\n"
                 f"Status: Complete\n\n"
                 f"Summary:\n"
                 f"This report covers the monthly operations.\n"
                 f"All tasks were completed on schedule.\n"
                 f"The team performed well this period.\n\n"
                 f"Key Metrics:\n"
                 f"- Tasks completed: {i * 10}\n"
                 f"- Issues resolved: {i * 2}\n"
                 f"- Team members: {i % 10 + 3}\n\n"
                 f"Conclusion:\n"
                 f"Overall performance was satisfactory.\n"
                 f"Next period goals have been established.\n\n"
             ) * 15,
             'w'),

            # Notes text - LOW entropy (3-4)
            ("notes_{}.txt",
             lambda i: (
                 f"Meeting Notes - Session {i}\n"
                 f"Attendees: Alice, Bob, Charlie\n"
                 f"Location: Conference Room\n\n"
                 f"Agenda Items:\n"
                 f"Item one: Review previous action items\n"
                 f"Item two: Discuss current progress\n"
                 f"Item three: Plan next steps\n\n"
                 f"Discussion:\n"
                 f"The team reviewed all pending items.\n"
                 f"Progress was reported by each member.\n"
                 f"Action items were assigned accordingly.\n\n"
                 f"Next Meeting: Next week same time.\n\n"
             ) * 18,
             'w'),

            # CSV data - LOW-MEDIUM entropy (4-5)
            ("data_{}.csv",
             lambda i: (
                 "id,name,department,salary,date\n" +
                 "\n".join([
                     f"{j},Employee{j},Department{j%5+1},"
                     f"{30000 + j*100},2024-01-{(j%28)+1:02d}"
                     for j in range(1, 80)
                 ])
             ),
             'w'),

            # Structured binary - MEDIUM entropy (5-6)
            # Uses repeating patterns NOT random bytes
            ("backup_{}.dat",
             lambda i: bytes([
                 (j * i) % 64 + 32    # repeating structured pattern
                 for j in range(8000)
             ]),
             'wb'),
        ]

        self.files = []
        file_num = 0

        while len(self.files) < num_files:
            template = templates[file_num % len(templates)]
            filename_pattern, content_gen, mode = template

            filename = filename_pattern.format(file_num + 1)
            filepath = os.path.join(self.base_dir, filename)

            try:
                content = content_gen(file_num + 1)
                with open(filepath, mode) as f:
                    f.write(content)
                self.files.append(filepath)
                file_num += 1

            except Exception as e:
                log.error(f"Could not create {filename}: {e}")
                file_num += 1

        log.info(f"Created {len(self.files)} test files")
        return self.files

    def cleanup(self):
        """Remove all test files and the test directory."""
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)
            log.info(f"Cleaned up: {self.base_dir}")

    def get_files(self):
        """Return list of all test file paths."""
        if os.path.exists(self.base_dir):
            return [
                os.path.join(self.base_dir, f)
                for f in os.listdir(self.base_dir)
                if os.path.isfile(os.path.join(self.base_dir, f))
            ]
        return []


# ============================================================
# NORMAL USER SIMULATOR
# Simulates what a REAL USER does with files.
# Used to generate "normal" training data for the AI.
# ============================================================

class NormalUserSimulator:
    """
    Simulates normal user file activity.

    A real user:
    - Opens one file at a time
    - Reads and edits slowly
    - Saves occasionally
    - Doesn't modify 50 files per second
    """

    def __init__(self, test_dir: str, duration: int = 30):
        self.test_dir = test_dir
        self.duration = duration
        self.stop_event = Event()
        self.stats = {
            'files_modified': 0,
            'start_time'    : None,
            'end_time'      : None,
        }

    def run(self):
        """Simulate normal user activity."""
        log.info("")
        log.info("=" * 50)
        log.info("NORMAL USER SIMULATION STARTING")
        log.info("=" * 50)
        log.info(f"Duration: {self.duration} seconds")
        log.info("Simulating slow, normal file edits...")
        log.info("")

        self.stats['start_time'] = time.time()
        env = TestEnvironment(self.test_dir)
        files = env.setup(num_files=20)

        if not files:
            log.error("No files to work with!")
            return

        end_time = time.time() + self.duration

        while time.time() < end_time and not self.stop_event.is_set():
            # Pick a random file
            target = random.choice(files)

            if not os.path.exists(target):
                continue

            # Simulate reading and editing (slow)
            try:
                # Read the file
                with open(target, 'r', errors='ignore') as f:
                    content = f.read()

                # Make a small edit
                edited = content + f"\n[Edited at {datetime.now()}]"

                # Write back
                with open(target, 'w') as f:
                    f.write(edited)

                self.stats['files_modified'] += 1
                log.info(f"[NORMAL] Edited: {os.path.basename(target)}")

            except Exception as e:
                log.debug(f"Edit error: {e}")

            # Normal user waits between edits (3-8 seconds)
            wait_time = random.uniform(3.0, 8.0)
            self.stop_event.wait(wait_time)

        self.stats['end_time'] = time.time()
        duration = self.stats['end_time'] - self.stats['start_time']
        rate = self.stats['files_modified'] / max(duration, 1)

        log.info("")
        log.info("NORMAL USER SIMULATION COMPLETE")
        log.info(f"Files modified : {self.stats['files_modified']}")
        log.info(f"Duration       : {duration:.1f} seconds")
        log.info(f"Rate           : {rate:.2f} files/sec (NORMAL)")

    def stop(self):
        self.stop_event.set()


# ============================================================
# RANSOMWARE SIMULATOR
# Simulates ransomware behavior patterns.
# Used to generate "malicious" training data.
# ============================================================

class RansomwareSimulator:
    """
    Safely simulates ransomware behavior.

    Real ransomware behavior patterns:
    1. Enumerates all files rapidly
    2. Reads each file
    3. Overwrites with encrypted content (we use random bytes)
    4. Renames file with new extension (.locked, .encrypted)
    5. Does this to ALL files as fast as possible

    Our simulation:
    - Only works in designated test folder
    - Uses os.urandom() instead of real encryption
    - Renames to .locked extension
    - Tracks all actions for audit
    """

    def __init__(self, test_dir: str):
        self.test_dir   = test_dir
        self.stop_event = Event()
        self.stats = {
            'files_encrypted'   : 0,
            'files_renamed'     : 0,
            'bytes_written'     : 0,
            'start_time'        : None,
            'end_time'          : None,
            'peak_rate'         : 0.0,
        }

    def run(self, speed: str = 'fast'):
        """
        Run the ransomware simulation.

        Args:
            speed: 'slow' (2 files/sec)
                   'medium' (5 files/sec)
                   'fast' (15+ files/sec)
        """

        # Speed settings
        speed_settings = {
            'slow'  : (0.4, 0.6),    # delay between files
            'medium': (0.1, 0.2),
            'fast'  : (0.01, 0.05),
        }
        delay_range = speed_settings.get(speed, (0.05, 0.1))

        log.info("")
        log.info("=" * 50)
        log.info("RANSOMWARE SIMULATION STARTING")
        log.info("=" * 50)
        log.info(f"Speed setting  : {speed}")
        log.info(f"Target folder  : {self.test_dir}")
        log.info(f"Delay per file : {delay_range[0]}-{delay_range[1]}s")
        log.info("")
        log.info("WARNING: This will rapidly modify all test files.")
        log.info("Your detection system should catch this!")
        log.info("")

        # Countdown
        for i in range(3, 0, -1):
            log.info(f"Starting in {i}...")
            time.sleep(1)

        log.info("RANSOMWARE SIMULATION ACTIVE")
        log.info("")

        self.stats['start_time'] = time.time()

        # Get all files in test directory
        env   = TestEnvironment(self.test_dir)
        files = env.get_files()

        if not files:
            log.error("No files found to simulate on!")
            log.error(f"Check folder: {self.test_dir}")
            return

        log.info(f"Found {len(files)} files to process")

        # Track rate
        recent_times = []

        # Process each file (simulate encryption)
        for i, filepath in enumerate(files):
            if self.stop_event.is_set():
                log.info("Simulation stopped by user")
                break

            if not os.path.exists(filepath):
                continue

            try:
                # Step 1: Get original file size
                original_size = os.path.getsize(filepath)

                # Step 2: Generate "encrypted" content
                # In real ransomware this would be AES-encrypted content
                # We use random bytes which have identical entropy profile
                encrypted_size = max(original_size, 1000)
                encrypted_content = os.urandom(encrypted_size)

                # Step 3: Overwrite file with "encrypted" content
                with open(filepath, 'wb') as f:
                    f.write(encrypted_content)

                self.stats['files_encrypted'] += 1
                self.stats['bytes_written']   += encrypted_size

                # Step 4: Rename with .locked extension
                # (some ransomware does this, some don't)
                if i % 3 == 0:    # rename every 3rd file
                    new_path = filepath + '.locked'
                    os.rename(filepath, new_path)
                    self.stats['files_renamed'] += 1
                    display_name = os.path.basename(new_path)
                else:
                    display_name = os.path.basename(filepath)

                # Step 5: Track rate
                now = time.time()
                recent_times.append(now)
                # Keep only last 5 seconds
                recent_times = [t for t in recent_times
                               if now - t <= 5.0]
                current_rate = len(recent_times) / 5.0

                if current_rate > self.stats['peak_rate']:
                    self.stats['peak_rate'] = current_rate

                # Log each file processed
                log.info(
                    f"[{i+1:3d}/{len(files)}] "
                    f"ENCRYPTED: {display_name:35} | "
                    f"Rate: {current_rate:.1f} files/sec"
                )

            except PermissionError:
                log.warning(f"Permission denied: {filepath}")
            except Exception as e:
                log.error(f"Error processing {filepath}: {e}")

            # Delay between files (simulates encryption time)
            delay = random.uniform(*delay_range)
            time.sleep(delay)

        # Simulation complete
        self.stats['end_time'] = time.time()
        self._print_summary(len(files))

    def _print_summary(self, total_files):
        """Print simulation summary."""
        duration = self.stats['end_time'] - self.stats['start_time']
        avg_rate = (self.stats['files_encrypted'] /
                   max(duration, 1))

        log.info("")
        log.info("=" * 50)
        log.info("RANSOMWARE SIMULATION COMPLETE")
        log.info("=" * 50)
        log.info(f"Files processed  : {self.stats['files_encrypted']}"
                f"/{total_files}")
        log.info(f"Files renamed    : {self.stats['files_renamed']}")
        log.info(f"Bytes written    : {self.stats['bytes_written']:,}")
        log.info(f"Duration         : {duration:.1f} seconds")
        log.info(f"Average rate     : {avg_rate:.1f} files/sec")
        log.info(f"Peak rate        : {self.stats['peak_rate']:.1f} files/sec")
        log.info("")
        log.info("If ENTROPY detected this, you will see")
        log.info("HIGH SPEED and HIGH ENTROPY alerts above.")

    def stop(self):
        self.stop_event.set()


# ============================================================
# TRAINING DATA GENERATOR
# Runs both simulations and saves labeled data for DQN.
# ============================================================

class TrainingDataGenerator:
    """
    Generates labeled training data for the DQN model.

    Runs normal and ransomware simulations,
    collects feature vectors,
    saves labeled data to files.
    """

    def __init__(self):
        self.training_data = []

    def generate_normal_samples(self, count: int = 100):
        """Generate feature vectors for NORMAL behavior."""
        log.info(f"Generating {count} normal behavior samples...")

        samples = []
        for i in range(count):
            # Simulate normal user behavior features
            sample = {
                'label'            : 0,       # 0 = normal
                'entropy_score'    : random.uniform(3.0, 6.5),
                'entropy_delta'    : random.uniform(-0.3, 0.3),
                'files_per_sec'    : random.uniform(0.01, 0.5),
                'ext_changed'      : 0,
                'process_age_sec'  : random.uniform(300, 7200),
                'files_affected'   : random.randint(1, 3),
                'avg_entropy_hist' : random.uniform(3.5, 6.0),
                'time_hour'        : random.randint(8, 20),
            }
            samples.append(sample)

        log.info(f"Generated {len(samples)} normal samples")
        return samples

    def generate_ransomware_samples(self, count: int = 100):
        """Generate feature vectors for RANSOMWARE behavior."""
        log.info(f"Generating {count} ransomware behavior samples...")

        samples = []
        for i in range(count):
            # Simulate ransomware behavior features
            sample = {
                'label'            : 1,       # 1 = ransomware
                'entropy_score'    : random.uniform(7.5, 8.0),
                'entropy_delta'    : random.uniform(2.0, 5.0),
                'files_per_sec'    : random.uniform(5.0, 50.0),
                'ext_changed'      : random.randint(0, 1),
                'process_age_sec'  : random.uniform(1, 60),
                'files_affected'   : random.randint(10, 200),
                'avg_entropy_hist' : random.uniform(7.0, 8.0),
                'time_hour'        : random.randint(0, 23),
            }
            samples.append(sample)

        log.info(f"Generated {len(samples)} ransomware samples")
        return samples

    def generate_and_save(self, normal_count=200,
                          ransomware_count=200, seed=1337):
        """Generate a versioned train/eval split with a fixed seed."""
        from data.training_schema import write_dataset, load_samples

        log.info("")
        log.info("=" * 50)
        log.info("GENERATING TRAINING DATA")
        log.info("=" * 50)

        train_path, eval_path = write_dataset(
            config.TRAINING_DATA_DIR,
            seed=seed,
            normal_count=normal_count,
            ransomware_count=ransomware_count,
        )
        samples = load_samples(train_path)
        log.info("Train: %s (%d samples)", train_path, len(samples))
        log.info("Eval : %s", eval_path)
        return str(train_path), samples


# ============================================================
# MAIN MENU
# ============================================================

def print_menu():
    print()
    print("=" * 55)
    print("  ENTROPY - Ransomware Simulator")
    print("=" * 55)
    print()
    print("  1. Setup test environment (create test files)")
    print("  2. Run NORMAL user simulation")
    print("  3. Run RANSOMWARE simulation (FAST)")
    print("  4. Run RANSOMWARE simulation (SLOW - for testing)")
    print("  5. Generate AI training data")
    print("  6. Clean up test files")
    print("  0. Exit")
    print()


if __name__ == "__main__":

    TEST_DIR = os.path.join(config.TESTING_DATA_DIR, "sim_files")

    while True:
        print_menu()
        choice = input("  Enter choice (0-6): ").strip()

        if choice == '0':
            print("Exiting simulator.")
            break

        elif choice == '1':
            print()
            env = TestEnvironment(TEST_DIR)
            files = env.setup(num_files=30)
            print()
            print(f"Test environment ready: {len(files)} files created")
            print(f"Location: {TEST_DIR}")

        elif choice == '2':
            print()
            print("Starting normal user simulation...")
            print("Run the pipeline in another terminal to see detection.")
            print()
            sim = NormalUserSimulator(TEST_DIR, duration=30)
            sim.run()

        elif choice == '3':
            print()
            print("FAST ransomware simulation.")
            print("Make sure the pipeline is running in another terminal!")
            print()

            # Setup files first if needed
            env = TestEnvironment(TEST_DIR)
            if not env.get_files():
                print("Setting up test files first...")
                env.setup(num_files=30)

            sim = RansomwareSimulator(TEST_DIR)
            try:
                sim.run(speed='fast')
            except KeyboardInterrupt:
                sim.stop()
                print("\nSimulation interrupted.")

        elif choice == '4':
            print()
            print("SLOW ransomware simulation (easier to observe).")
            print("Make sure the pipeline is running in another terminal!")
            print()

            env = TestEnvironment(TEST_DIR)
            if not env.get_files():
                print("Setting up test files first...")
                env.setup(num_files=30)

            sim = RansomwareSimulator(TEST_DIR)
            try:
                sim.run(speed='slow')
            except KeyboardInterrupt:
                sim.stop()
                print("\nSimulation interrupted.")

        elif choice == '5':
            print()
            gen = TrainingDataGenerator()
            path, samples = gen.generate_and_save(
                normal_count=300,
                ransomware_count=300
            )
            print(f"Training data ready: {len(samples)} samples")

        elif choice == '6':
            print()
            env = TestEnvironment(TEST_DIR)
            env.cleanup()
            print("Test files cleaned up.")

        else:
            print("Invalid choice. Try again.")