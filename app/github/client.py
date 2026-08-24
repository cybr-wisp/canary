import httpx

from app.config import settings
from app.github.auth import create_app_jwt
from app.models import ChangedFile


class GitHubClient:
    def __init__(self) -> None:
        self.api_url = settings.github_api_url.rstrip("/")

    async def get_installation_token(
        self,
        installation_id: int,
    ) -> str:
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

        return response.json()["token"]

    async def get_pull_request_files(
        self,
        repository: str,
        pull_number: int,
        installation_id: int,
    ) -> list[ChangedFile]:
        token = await self.get_installation_token(
            installation_id
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = (
            f"{self.api_url}/repos/{repository}/"
            f"pulls/{pull_number}/files"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                timeout=10.0,
            )
            response.raise_for_status()

        return [
            ChangedFile(
                filename=file["filename"],
                patch=file.get("patch", ""),
                additions=file.get("additions", 0),
                deletions=file.get("deletions", 0),
            )
            for file in response.json()
        ]

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