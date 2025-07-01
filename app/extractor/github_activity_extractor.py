from app.schemas.github_activity import CommitEntry, IssueEntry, PullRequestEntry, ReadmeInfo
from app.vectordb.schema import BaseRecord, GitCommitMetadata, GitIssueMetadata, GitPRMetadata, GitReadMeMetadata


def extract_record_from_commit_entry(
    commit_entry: CommitEntry,
) -> BaseRecord[GitCommitMetadata]:
    return BaseRecord[GitCommitMetadata](
        text=(commit_entry.message or "").strip(),
        metadata=GitCommitMetadata(
            author=commit_entry.author or 0,
            date=commit_entry.date,
            type="commit",
            title=commit_entry.message,
            repo_name=commit_entry.repo,
            sha=commit_entry.sha
        )
    )

def extract_record_from_pull_request_entry(
    pr_entry: PullRequestEntry,
) -> BaseRecord[GitPRMetadata]:
    return BaseRecord[GitPRMetadata](
        text=(pr_entry.content or "").strip(),
        metadata=GitPRMetadata(
            author=pr_entry.author or 0,
            date=pr_entry.created_at,
            type="pull_request",
            title=pr_entry.title,
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
            author=issue_entry.author or 0,
            date=issue_entry.created_at,
            type="issue",
            title=issue_entry.title,
            repo_name=issue_entry.repo,
            number=issue_entry.number
        )
    )

def extract_record_from_readme(
    readme: ReadmeInfo,
) -> BaseRecord[GitReadMeMetadata]:
    return BaseRecord[GitReadMeMetadata](
        text=readme.content.strip(),
        metadata=GitReadMeMetadata(
            repo_name=readme.repo_name,
            html_url=readme.html_url,
            download_url=readme.download_url
        )
    )
