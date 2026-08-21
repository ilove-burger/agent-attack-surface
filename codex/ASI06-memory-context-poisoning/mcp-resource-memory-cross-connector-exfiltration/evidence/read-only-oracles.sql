SELECT
    id,
    datetime(updated_at, 'unixepoch') AS updated_at_utc,
    source,
    memory_mode,
    has_user_event,
    cli_version,
    model,
    approval_mode,
    sandbox_policy
FROM threads
ORDER BY updated_at;

SELECT
    kind,
    job_key,
    status,
    datetime(started_at, 'unixepoch') AS started_at_utc,
    datetime(finished_at, 'unixepoch') AS finished_at_utc,
    datetime(retry_at, 'unixepoch') AS retry_at_utc,
    retry_remaining,
    last_error
FROM jobs
ORDER BY kind, job_key;

SELECT
    thread_id,
    source_updated_at,
    length(raw_memory) AS raw_memory_bytes,
    length(rollout_summary) AS rollout_summary_bytes,
    rollout_slug,
    selected_for_phase2
FROM stage1_outputs
ORDER BY source_updated_at;
