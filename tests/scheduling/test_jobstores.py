import pytest

from search_gov_crawler.scheduling.jobstores import SpiderRedisJobStore


class MockRedisClient:
    @staticmethod
    def zadd(*_args, **_kwargs):
        return True

    @staticmethod
    def zrem(*_args, **_kwargs):
        return True

    @staticmethod
    def delete(*_args, **_kwargs):
        return True

    @staticmethod
    def zrange(*_args, jobs_to_output, **_kwargs):
        return jobs_to_output

    @staticmethod
    def lookup_job(*_args, **_kwargs):
        return True


@pytest.fixture(name="simple_jobstore")
def fixture_simple_jobstore():
    jobstore = SpiderRedisJobStore(pending_jobs_key="test_pending_jobs")
    jobstore.redis = MockRedisClient()
    return jobstore


def test_init(simple_jobstore):
    assert simple_jobstore.pending_jobs_key == "test_pending_jobs"


def test_alias_without_scheduler(simple_jobstore):
    with pytest.raises(ValueError, match="Job store alias is not set. Please set the alias before using it."):
        simple_jobstore.alias


@pytest.mark.parametrize(
    ("method", "args", "expected_log_message"),
    [
        ("add_pending_job", ["test1"], "Added test1 to pending jobs key test_pending_jobs"),
        ("remove_pending_job", ["test1"], "Removed test1 from pending jobs key test_pending_jobs"),
        ("remove_all_pending_jobs", [], "Removed all pending jobs from key test_pending_jobs"),
    ],
)
def test_basic_commands(caplog, simple_jobstore, method, args, expected_log_message):
    with caplog.at_level("DEBUG"):
        getattr(simple_jobstore, method)(*args)

    assert expected_log_message in caplog.messages


@pytest.mark.parametrize("pending_job_ids", [[b"test::job1", b"test::job2"], []])
def test_get_all_pending_jobs(caplog, simple_jobstore, monkeypatch, pending_job_ids):
    monkeypatch.setattr(SpiderRedisJobStore, "lookup_job", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(MockRedisClient, "zrange", lambda *_args, **_kwargs: pending_job_ids)

    with caplog.at_level("DEBUG"):
        simple_jobstore.get_all_pending_jobs(rerun_prefix="test::")

    assert f"Found and retrieved {len(pending_job_ids)} pending jobs from key test_pending_jobs" in caplog.messages
