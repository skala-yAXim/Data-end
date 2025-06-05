from app.schemas.github_activity import CommitEntry, IssueEntry, PullRequestEntry
from app.vectordb.schema import BaseRecord, GitCommitMetadata, GitIssueMetadata, GitPRMetadata


def extract_record_from_commit_entry(
    commit_entry: CommitEntry,
) -> BaseRecord[GitCommitMetadata]:
    return BaseRecord[GitCommitMetadata](
        text=(commit_entry.message or "").strip(),
        metadata=GitCommitMetadata(
            author=commit_entry.author or "unknown",
            date=commit_entry.date,
            type="commit",
            repo_name=commit_entry.repo,
            sha=commit_entry.sha
        )
    )

def extract_record_from_pull_request_entry(
    pr_entry: PullRequestEntry,
) -> BaseRecord[GitPRMetadata]:
    return BaseRecord[GitPRMetadata](
        text=((pr_entry.title or "") + "\n\n" + (pr_entry.content or "")).strip(),
        metadata=GitPRMetadata(
            author=pr_entry.author or "unknown",
            date=pr_entry.created_at,
            type="pull_request",
            repo_name=pr_entry.repo,
            number=pr_entry.number,
            state=pr_entry.state
        )
    )

def extract_record_from_issue_entry(
    issue_entry: IssueEntry,
) -> BaseRecord[GitIssueMetadata]:
    return BaseRecord[GitIssueMetadata](
        text=(issue_entry.title or "").strip(),
        metadata=GitIssueMetadata(
            author=issue_entry.author or "unknown",
            date=issue_entry.created_at,
            type="issue",
            repo_name=issue_entry.repo,
            number=issue_entry.number
        )
    )
