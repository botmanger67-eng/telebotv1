import logging
from typing import Optional, Dict, Any
import httpx
import re
from urllib.parse import urlparse

from src.config import GITHUB_TOKEN, GITHUB_API_BASE_URL
from src.link_checker import extract_repo_from_url  # Assume this function exists
from src.database import get_db, save_repo_data  # Assume these functions exist

logger = logging.getLogger(__name__)

# Default headers for GitHub API
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "TelegramBot/1.0",
}

if GITHUB_TOKEN:
    DEFAULT_HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"


class GitHubTools:
    """Handles fetching and analyzing GitHub repository information."""

    def __init__(self):
        self.client = httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def fetch_repo_info(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch general information about a GitHub repository.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.

        Returns:
            Dictionary containing repo metadata if successful, else None.

        Raises:
            httpx.HTTPStatusError: On API errors.
        """
        url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return {
                "name": data.get("full_name"),
                "description": data.get("description"),
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "language": data.get("language"),
                "topics": data.get("topics", []),
                "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
                "url": data.get("html_url"),
                "owner_avatar": data.get("owner", {}).get("avatar_url"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "open_issues": data.get("open_issues_count"),
                "default_branch": data.get("default_branch"),
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Repository %s/%s not found", owner, repo)
                return None
            elif e.response.status_code == 403:
                logger.error("GitHub API rate limit exceeded or token invalid")
                raise
            else:
                logger.error("HTTP error fetching repo %s/%s: %s", owner, repo, e)
                raise
        except httpx.RequestError as e:
            logger.error("Request failed for repo %s/%s: %s", owner, repo, e)
            raise

    async def fetch_repo_stats(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch additional statistics for a GitHub repository.

        Includes: contributors count, releases count, last commit date.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Dictionary with extra stats, or None if not found.
        """
        try:
            # Get contributions count (may be heavy; use a simple approach)
            contributors_url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contributors?per_page=1&anon=true"
            contrib_response = await self.client.get(contributors_url)
            contrib_response.raise_for_status()
            # Extract total count from Link header if present
            link_header = contrib_response.headers.get("Link", "")
            total_contributors = self._extract_total_count_from_link(link_header) or 0

            # Get releases count
            releases_url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/releases?per_page=1"
            releases_response = await self.client.get(releases_url)
            releases_response.raise_for_status()
            total_releases = self._extract_total_count_from_link(releases_response.headers.get("Link", "")) or 0

            # Get last commit date (optional)
            commits_url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/commits?per_page=1"
            commits_response = await self.client.get(commits_url)
            commits_response.raise_for_status()
            last_commit = None
            if commits_response.status_code == 200 and len(commits_response.json()) > 0:
                last_commit = commits_response.json()[0].get("commit", {}).get("committer", {}).get("date")

            return {
                "total_contributors": total_contributors,
                "total_releases": total_releases,
                "last_commit_date": last_commit,
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error("Stats fetch failed for %s/%s: %s", owner, repo, e)
            return None
        except Exception as e:
            logger.error("Unexpected error fetching stats: %s", e)
            return None

    def _extract_total_count_from_link(self, link_header: str) -> Optional[int]:
        """Extract total count from GitHub API Link header (last page number)."""
        if not link_header:
            return None
        # Example: <https://api.github.com/repos/...?page=2>; rel="last"
        match = re.search(r'page=(\d+)>; rel="last"', link_header)
        if match:
            return int(match.group(1))
        # If there's no 'last', there is only one page
        return 1

    async def get_repo_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse a GitHub URL and fetch repository information.

        Args:
            url: Full GitHub URL (e.g., https://github.com/owner/repo).

        Returns:
            Combined repo info and stats, or None if invalid/not found.
        """
        # Attempt to use link_checker's extraction function if available
        extracted = extract_repo_from_url(url)
        if extracted:
            owner, repo = extracted
        else:
            # Fallback regex
            match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', url)
            if not match:
                logger.warning("Invalid GitHub URL: %s", url)
                return None
            owner, repo = match.group(1), match.group(2).rstrip('/')

        info = await self.fetch_repo_info(owner, repo)
        if not info:
            return None
        stats = await self.fetch_repo_stats(owner, repo)
        if stats:
            info.update(stats)

        # Optionally cache in database
        try:
            db = get_db()
            save_repo_data(db, info)  # Assume this function stores the data
        except Exception as e:
            logger.warning("Failed to cache repo data: %s", e)

        return info

    async def analyze_github_link(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and analyze a GitHub repository link from text.

        Returns None if no valid repository link found.
        """
        # Use more flexible regex to find github.com/owner/repo patterns
        pattern = r'https?://github\.com/[^/\s]+/[^/\s]+'
        match = re.search(pattern, text)
        if not match:
            return None
        url = match.group(0).rstrip('/')
        # Remove trailing slash and any query/fragment
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return await self.get_repo_by_url(clean_url)

    async def format_repo_message(self, repo_data: Dict[str, Any]) -> str:
        """Format repository data into a readable message for Telegram.

        Args:
            repo_data: Dictionary from get_repo_by_url.

        Returns:
            Formatted message string.
        """
        lines = [
            f"📦 <b>{repo_data['name']}</b>",
            f"📝 {repo_data.get('description', 'No description')}",
            f"⭐ {repo_data.get('stars', 0)} stars | 🍴 {repo_data.get('forks', 0)} forks",
            f"💻 Language: {repo_data.get('language', 'Unknown')}",
            f"📋 License: {repo_data.get('license', 'None')}",
            f"🐛 Open issues: {repo_data.get('open_issues', 0)}",
            f"👥 Contributors: {repo_data.get('total_contributors', 'N/A')}",
            f"📦 Releases: {repo_data.get('total_releases', 'N/A')}",
            f"🕐 Last commit: {repo_data.get('last_commit_date', 'Unknown')[:10] if repo_data.get('last_commit_date') else 'Unknown'}",
            f"🔗 <a href='{repo_data['url']}'>Open on GitHub</a>",
        ]
        if repo_data.get('topics'):
            lines.append(f"🏷 Topics: {' '.join(repo_data['topics'])}")
        return '\n'.join(lines)


# Singleton pattern or just instantiate as needed
github_tools = GitHubTools()

__all__ = ['github_tools', 'GitHubTools']