# test_blockchain.py
import sys
sys.path.append(r"C:\Entropy")

from blockchain.connector import BlockchainConnector

print("=" * 50)
print("  BLOCKCHAIN CONNECTION TEST")
print("=" * 50)

bc = BlockchainConnector()

print("\n[TEST 1] Logging a test event...")
receipt = bc.log_event({
    "fingerprint" : "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
    "threat_type" : "ransomware",
    "pid"         : 9999,
    "entropy"     : 7.91,
    "process"     : "test_ransomware.exe",
    "file_path"   : r"C:\Users\User\Documents\test.jpg",
    "action"      : "TERMINATE+QUARANTINE",
    "status"      : "confirmed"
})

if receipt:
    print(f"\n✅ TEST 1 PASSED")
    print(f"   TX: {receipt.transactionHash.hex()}")
else:
    print(f"\n❌ TEST 1 FAILED")

print("\n[TEST 2] Reading events from chain...")
events = bc.get_all_events()
print(f"   Total events on chain: {len(events)}")

for e in events:
    print(f"\n   Event #{e['id']}")
    print(f"   Fingerprint : {e['fingerprint']}")
    print(f"   Process     : {e['processName']}")
    print(f"   Entropy     : {e['entropy']}")
    print(f"   Action      : {e['actionTaken']}")
    print(f"   Status      : {e['status']}")

print("\n[TEST 3] Chain connection status...")
status = bc.verify_chain()
print(f"   Connected: {status}")

print("\n" + "=" * 50)
print("  ALL TESTS COMPLETE")
print("=" * 50)