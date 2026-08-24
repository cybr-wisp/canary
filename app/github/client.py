from __future__ import annotations

import base64
from urllib.parse import quote

import httpx

from app.config import settings
from app.github.auth import create_app_jwt
from app.models import ChangedFile


class GitHubClient:
    def __init__(self) -> None:
        self.api_url = settings.github_api_url.rstrip("/")

        # A GitHubClient instance is created for one PR analysis,
        # so caching the installation token prevents unnecessary
        # token requests during repository traversal.
        self._installation_tokens: dict[
            int,
            str,
        ] = {}

    def _headers(
        self,
        token: str,
    ) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_installation_token(
        self,
        installation_id: int,
    ) -> str:
        cached = self._installation_tokens.get(
            installation_id
        )

        if cached is not None:
            return cached

        app_jwt = create_app_jwt(
            app_id=settings.github_app_id,
            private_key_path=settings.github_private_key_path,
        )

        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = (
            f"{self.api_url}/app/installations/"
            f"{installation_id}/access_tokens"
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                timeout=10.0,
            )

            response.raise_for_status()

        token = response.json()["token"]

        self._installation_tokens[
            installation_id
        ] = token

        return token

    async def get_pull_request_refs(
        self,
        repository: str,
        pull_number: int,
        installation_id: int,
    ) -> tuple[str, str]:
        """
        Return:

            (base_sha, head_sha)

        for a pull request.

        Canary v2 compares source at these two repository states.
        """

        token = await self.get_installation_token(
            installation_id
        )

        url = (
            f"{self.api_url}/repos/{repository}/"
            f"pulls/{pull_number}"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._headers(token),
                timeout=10.0,
            )

            response.raise_for_status()

        data = response.json()

        return (
            data["base"]["sha"],
            data["head"]["sha"],
        )

    async def get_pull_request_files(
        self,
        repository: str,
        pull_number: int,
        installation_id: int,
    ) -> list[ChangedFile]:
        """
        Fetch every changed file in the PR.

        Pagination is handled so Canary is not limited to GitHub's
        first page of changed files.
        """

        token = await self.get_installation_token(
            installation_id
        )

        url = (
            f"{self.api_url}/repos/{repository}/"
            f"pulls/{pull_number}/files"
        )

        files: list[dict] = []

        page = 1

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    url,
                    headers=self._headers(token),
                    params={
                        "per_page": 100,
                        "page": page,
                    },
                    timeout=10.0,
                )

                response.raise_for_status()

                page_files = response.json()

                files.extend(
                    page_files
                )

                if len(page_files) < 100:
                    break

                page += 1

        return [
            ChangedFile(
                filename=file["filename"],
                patch=file.get("patch", ""),
                additions=file.get(
                    "additions",
                    0,
                ),
                deletions=file.get(
                    "deletions",
                    0,
                ),
                status=file.get(
                    "status",
                    "modified",
                ),
                previous_filename=file.get(
                    "previous_filename"
                ),
            )
            for file in files
        ]

    async def get_python_file_source(
        self,
        repository: str,
        path: str,
        ref: str,
        installation_id: int,
    ) -> str | None:
        """
        Fetch one Python file at an exact repository ref.

        Returns None when the path does not exist at that ref.

        This is particularly useful for:

        - newly added files
        - deleted files
        - renamed files
        """

        token = await self.get_installation_token(
            installation_id
        )

        encoded_path = quote(
            path,
            safe="/",
        )

        url = (
            f"{self.api_url}/repos/{repository}/"
            f"contents/{encoded_path}"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._headers(token),
                params={
                    "ref": ref,
                },
                timeout=10.0,
            )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        data = response.json()

        if data.get("type") != "file":
            return None

        encoded = data.get(
            "content",
            "",
        )

        raw = base64.b64decode(
            encoded
        )

        return raw.decode(
            "utf-8"
        )

    async def get_repository_python_sources(
        self,
        repository: str,
        ref: str,
        installation_id: int,
    ) -> dict[str, str]:
        """
        Fetch the Python source snapshot of a repository at `ref`.

        The Git tree identifies every Python blob and Canary then
        fetches each blob's source.

        Returns:

            {
                "app/users.py": "...",
                "app/api.py": "...",
                ...
            }

        This becomes the repository-wide HEAD snapshot used by
        Canary's call-site and dependency analysis.
        """

        token = await self.get_installation_token(
            installation_id
        )

        headers = self._headers(
            token
        )

        tree_url = (
            f"{self.api_url}/repos/{repository}/"
            f"git/trees/{ref}"
        )

        async with httpx.AsyncClient() as client:
            tree_response = await client.get(
                tree_url,
                headers=headers,
                params={
                    "recursive": "1",
                },
                timeout=20.0,
            )

            tree_response.raise_for_status()

            tree_data = (
                tree_response.json()
            )

            if tree_data.get(
                "truncated",
                False,
            ):
                raise RuntimeError(
                    "GitHub returned a truncated repository tree. "
                    "Canary cannot safely perform complete "
                    "repository impact analysis."
                )

            python_entries = [
                entry
                for entry in tree_data.get(
                    "tree",
                    [],
                )
                if (
                    entry.get("type")
                    == "blob"
                    and entry.get(
                        "path",
                        "",
                    ).endswith(".py")
                )
            ]

            sources: dict[
                str,
                str,
            ] = {}

            for entry in python_entries:
                blob_url = (
                    f"{self.api_url}/repos/"
                    f"{repository}/git/blobs/"
                    f"{entry['sha']}"
                )

                response = await client.get(
                    blob_url,
                    headers=headers,
                    timeout=20.0,
                )

                response.raise_for_status()

                blob = response.json()

                if blob.get(
                    "encoding"
                ) != "base64":
                    continue

                raw = base64.b64decode(
                    blob["content"]
                )

                try:
                    source = raw.decode(
                        "utf-8"
                    )

                except UnicodeDecodeError:
                    # Canary currently analyzes UTF-8 Python
                    # sources only. One unusual file should not
                    # destroy the complete repository snapshot.
                    continue

                sources[
                    entry["path"]
                ] = source

        return sources

    async def get_repository_installation_id(
        self,
        repository: str,
    ) -> int:
        """
        Find Canary's GitHub App installation for a repository.

        This lets the terminal CLI analyze a PR using only its URL,
        without requiring the user to provide an installation ID.
        """

        app_jwt = create_app_jwt(
            app_id=settings.github_app_id,
            private_key_path=settings.github_private_key_path,
        )

        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = (
            f"{self.api_url}/repos/"
            f"{repository}/installation"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                timeout=10.0,
            )

            response.raise_for_status()

        data = response.json()

        return data["id"]