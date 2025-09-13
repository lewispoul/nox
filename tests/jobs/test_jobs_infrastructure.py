"""
Tests for NOX Jobs Infrastructure

Tests the job management infrastructure including states, storage, and manager.
"""

import shutil
import tempfile

import pytest

from nox.jobs.manager import JobManager
from nox.jobs.states import JobState, is_terminal_state, is_valid_transition
from nox.jobs.storage import JobStorage


class TestJobStates:
    """Test job state management and transitions"""

    def test_job_state_enum(self):
        """Test job state enumeration"""
        assert JobState.PENDING.value == "pending"
        assert JobState.RUNNING.value == "running"
        assert JobState.COMPLETED.value == "completed"
        assert JobState.FAILED.value == "failed"

    def test_valid_transitions(self):
        """Test valid state transitions"""
        # From PENDING
        assert is_valid_transition(JobState.PENDING, JobState.RUNNING)
        assert is_valid_transition(JobState.PENDING, JobState.FAILED)
        assert not is_valid_transition(JobState.PENDING, JobState.COMPLETED)

        # From RUNNING
        assert is_valid_transition(JobState.RUNNING, JobState.COMPLETED)
        assert is_valid_transition(JobState.RUNNING, JobState.FAILED)
        assert not is_valid_transition(JobState.RUNNING, JobState.PENDING)

        # Terminal states
        assert not is_valid_transition(JobState.COMPLETED, JobState.RUNNING)
        assert not is_valid_transition(JobState.FAILED, JobState.PENDING)

    def test_terminal_states(self):
        """Test terminal state identification"""
        assert not is_terminal_state(JobState.PENDING)
        assert not is_terminal_state(JobState.RUNNING)
        assert is_terminal_state(JobState.COMPLETED)
        assert is_terminal_state(JobState.FAILED)


class TestJobStorage:
    """Test job storage functionality"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing"""
        temp_dir = tempfile.mkdtemp()
        storage = JobStorage(temp_dir)
        yield storage
        shutil.rmtree(temp_dir)

    def test_save_and_load_job(self, temp_storage):
        """Test saving and loading job data"""
        job_id = "test_job_123"
        job_data = {"state": "pending", "message": "Test job", "progress": 0.0}

        # Save job
        temp_storage.save_job(job_id, job_data)

        # Load job
        loaded_data = temp_storage.load_job(job_id)
        assert loaded_data is not None
        assert loaded_data["state"] == "pending"
        assert loaded_data["message"] == "Test job"
        assert "_metadata" in loaded_data

    def test_load_nonexistent_job(self, temp_storage):
        """Test loading non-existent job returns None"""
        result = temp_storage.load_job("nonexistent")
        assert result is None

    def test_update_job_state(self, temp_storage):
        """Test updating job state"""
        job_id = "test_job_456"
        initial_data = {"state": "pending", "message": "Initial"}

        temp_storage.save_job(job_id, initial_data)

        # Update state
        success = temp_storage.update_job_state(
            job_id, JobState.RUNNING, "Processing", 0.5
        )
        assert success

        # Verify update
        updated_data = temp_storage.load_job(job_id)
        assert updated_data["state"] == "running"
        assert updated_data["message"] == "Processing"
        assert updated_data["progress"] == 0.5

    def test_set_job_result(self, temp_storage):
        """Test setting job result"""
        job_id = "test_job_789"
        initial_data = {"state": "running"}
        temp_storage.save_job(job_id, initial_data)

        result_data = {"output": "success", "artifacts": []}
        success = temp_storage.set_job_result(job_id, result_data)
        assert success

        job_data = temp_storage.load_job(job_id)
        assert job_data["result"] == result_data
        assert "completed_at" in job_data

    def test_list_jobs(self, temp_storage):
        """Test listing jobs with filtering"""
        # Create multiple jobs
        temp_storage.save_job("job1", {"state": "pending"})
        temp_storage.save_job("job2", {"state": "running"})
        temp_storage.save_job("job3", {"state": "completed"})

        # List all jobs
        all_jobs = temp_storage.list_jobs()
        assert len(all_jobs) == 3

        # List only pending jobs
        pending_jobs = temp_storage.list_jobs(JobState.PENDING)
        assert len(pending_jobs) == 1
        assert "job1" in pending_jobs

    def test_delete_job(self, temp_storage):
        """Test deleting a job"""
        job_id = "test_delete"
        temp_storage.save_job(job_id, {"state": "completed"})

        # Verify job exists
        assert temp_storage.load_job(job_id) is not None

        # Delete job
        success = temp_storage.delete_job(job_id)
        assert success

        # Verify job is gone
        assert temp_storage.load_job(job_id) is None


class TestJobManager:
    """Test job manager functionality"""

    @pytest.fixture
    def temp_manager(self):
        """Create temporary job manager for testing"""
        temp_dir = tempfile.mkdtemp()
        storage = JobStorage(temp_dir)
        manager = JobManager(storage)
        yield manager
        shutil.rmtree(temp_dir)

    def test_create_job(self, temp_manager):
        """Test job creation"""
        job_request = {"engine": "xtb", "inputs": {"xyz": "H 0 0 0"}}

        job_id = temp_manager.create_job(job_request)
        assert len(job_id) == 32  # UUID hex format

        # Verify job data
        job_data = temp_manager.get_job(job_id)
        assert job_data is not None
        assert job_data["state"] == "pending"
        assert job_data["request"] == job_request
        assert job_data["result"] is None

    def test_get_nonexistent_job(self, temp_manager):
        """Test getting non-existent job"""
        result = temp_manager.get_job("nonexistent")
        assert result is None

    def test_update_job_state_with_validation(self, temp_manager):
        """Test job state updates with transition validation"""
        job_id = temp_manager.create_job({"test": "data"})

        # Valid transition: pending -> running
        success = temp_manager.update_job_state(job_id, JobState.RUNNING, "Processing")
        assert success

        job_data = temp_manager.get_job(job_id)
        assert job_data["state"] == "running"

        # Invalid transition: running -> pending (should fail)
        success = temp_manager.update_job_state(
            job_id, JobState.PENDING, "Back to pending"
        )
        assert not success

        # State should remain unchanged
        job_data = temp_manager.get_job(job_id)
        assert job_data["state"] == "running"

    def test_set_job_result(self, temp_manager):
        """Test setting job result"""
        job_id = temp_manager.create_job({"test": "data"})

        result_data = {"scalars": {"energy": -1.0}, "artifacts": []}

        success = temp_manager.set_job_result(job_id, result_data)
        assert success

        job_data = temp_manager.get_job(job_id)
        assert job_data["result"] == result_data
        assert "completed_at" in job_data

    def test_set_job_failed(self, temp_manager):
        """Test marking job as failed"""
        job_id = temp_manager.create_job({"test": "data"})

        # First transition to running
        temp_manager.update_job_state(job_id, JobState.RUNNING)

        # Then mark as failed
        success = temp_manager.set_job_failed(job_id, "Test error")
        assert success

        job_data = temp_manager.get_job(job_id)
        assert job_data["state"] == "failed"
        assert job_data["message"] == "Test error"

    def test_list_jobs(self, temp_manager):
        """Test listing jobs"""
        # Create multiple jobs
        temp_manager.create_job({"name": "job1"})
        job2 = temp_manager.create_job({"name": "job2"})
        temp_manager.create_job({"name": "job3"})

        # Update one to running
        temp_manager.update_job_state(job2, JobState.RUNNING)

        # List all jobs
        all_jobs = temp_manager.list_jobs()
        assert len(all_jobs) == 3

        # List only pending jobs
        pending_jobs = temp_manager.list_jobs(JobState.PENDING)
        assert len(pending_jobs) == 2

        # List with limit
        limited_jobs = temp_manager.list_jobs(limit=2)
        assert len(limited_jobs) == 2

    def test_get_job_stats(self, temp_manager):
        """Test job statistics"""
        # Initially no jobs
        stats = temp_manager.get_job_stats()
        assert stats["total"] == 0
        assert stats["pending"] == 0

        # Create some jobs
        temp_manager.create_job({"name": "job1"})
        job2 = temp_manager.create_job({"name": "job2"})
        temp_manager.update_job_state(job2, JobState.RUNNING)

        stats = temp_manager.get_job_stats()
        assert stats["total"] == 2
        assert stats["pending"] == 1
        assert stats["running"] == 1
        assert stats["completed"] == 0
        assert stats["failed"] == 0
