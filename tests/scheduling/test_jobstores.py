import pytest

from search_gov_crawler.scheduling.jobstores import SpiderRedisJobStore


def test_init(mock_redis_jobstore):
    assert mock_redis_jobstore.pending_jobs_key == "test_pending_jobs"


def test_alias_without_scheduler(mock_redis_jobstore):
    mock_redis_jobstore._alias = None
    with pytest.raises(ValueError, match="Job store alias is not set. Please set the alias before using it."):
        mock_redis_jobstore.alias


@pytest.mark.parametrize(
    ("method", "args", "expected_log_message"),
    [
        ("add_pending_job", ["test1"], "Added test1 to pending jobs key test_pending_jobs"),
        ("remove_pending_job", ["test1"], "Removed test1 from pending jobs key test_pending_jobs"),
        ("remove_all_pending_jobs", [], "Removed all pending jobs from key test_pending_jobs"),
    ],
)
def test_basic_commands(caplog, mock_redis_jobstore, method, args, expected_log_message):
    with caplog.at_level("DEBUG"):
        getattr(mock_redis_jobstore, method)(*args)

    assert expected_log_message in caplog.messages


@pytest.mark.parametrize("pending_job_ids", [[b"test::job1", b"test::job2"], []])
def test_get_all_pending_jobs(caplog, mock_redis_jobstore, monkeypatch, pending_job_ids):
    monkeypatch.setattr(SpiderRedisJobStore, "lookup_job", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(mock_redis_jobstore.redis, "zrange", lambda *_args, **_kwargs: pending_job_ids)

    with caplog.at_level("DEBUG"):
        mock_redis_jobstore.get_all_pending_jobs(rerun_prefix="test::")

    expected_messages = (f"Found and retrieved {len(pending_job_ids)} pending jobs from key test_pending_jobs",)
    assert all(expected_message in caplog.messages for expected_message in expected_messages)
