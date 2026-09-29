// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ThreatLogger {
    struct ThreatEvent {
        uint256 id;
        string  fingerprint;
        string  threatType;
        uint256 timestamp;
        uint256 pid;
        uint256 entropyScore;
        string  processName;
        string  filePath;
        string  actionTaken;
        string  status;
    }

    ThreatEvent[] public events;
    address public owner;

    event ThreatLogged(
        uint256 indexed id,
        string fingerprint,
        string threatType,
        uint256 timestamp
    );

    constructor() { owner = msg.sender; }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function transferOwnership(address nextOwner) public onlyOwner {
        require(nextOwner != address(0), "zero owner");
        owner = nextOwner;
    }

    function logThreat(
        string memory fingerprint,
        string memory threatType,
        uint256 pid,
        uint256 entropyScore,
        string memory processName,
        string memory filePath,
        string memory actionTaken,
        string memory status
    ) public onlyOwner returns (uint256) {
        uint256 id = events.length;
        events.push(ThreatEvent(
            id, fingerprint, threatType, block.timestamp,
            pid, entropyScore, processName, filePath, actionTaken, status
        ));
        emit ThreatLogged(id, fingerprint, threatType, block.timestamp);
        return id;
    }

    function getEvent(uint256 id) public view returns (
        uint256, string memory, string memory, uint256,
        uint256, uint256, string memory, string memory, string memory, string memory
    ) {
        ThreatEvent memory e = events[id];
        return (e.id, e.fingerprint, e.threatType, e.timestamp,
                e.pid, e.entropyScore, e.processName, e.filePath, e.actionTaken, e.status);
    }

    function getEventCount() public view returns (uint256) { return events.length; }
    function getRecentEvents(uint256 count) public view returns (uint256[] memory) {
        uint256 len = events.length;
        uint256 n = count < len ? count : len;
        uint256[] memory ids = new uint256[](n);
        for (uint256 i = 0; i < n; i++) ids[i] = len - n + i;
        return ids;
    }
}