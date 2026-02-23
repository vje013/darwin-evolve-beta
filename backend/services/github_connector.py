"""
Darwin Enterprise Evolve Beta — GitHub Connector
Fetches PRs, issues, and recent commits from a GitHub repo.
Writes them as Entity nodes in Neo4j with five-edge-type relationships.
"""
import httpx
from datetime import datetime, timezone
from services.graph import merge_entity, set_entity_attribute, create_relationship, link_entity_to_room
from services.audit import audit

GITHUB_API = "https://api.github.com"


async def sync_github_repo(
    room_id: str,
    repo: str,
    token: str,
    user_id: str,
    since: str | None = None,
) -> dict:
    """
    Sync a GitHub repo into the graph.
    repo: "owner/repo" format
    token: GitHub personal access token
    since: ISO datetime string — only fetch items updated after this time
    Returns: summary of what was synced
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    summary = {"pull_requests": 0, "issues": 0, "commits": 0, "errors": []}

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # --- Create repo entity ---
        repo_entity_id = f"github_repo_{repo.replace('/', '_')}"
        merge_entity(repo_entity_id, "Repository", repo, source="github")
        set_entity_attribute(repo_entity_id, "url", f"https://github.com/{repo}", "string", "github")
        set_entity_attribute(repo_entity_id, "platform", "github", "string", "github")
        link_entity_to_room(repo_entity_id, room_id)

        # --- Pull Requests ---
        try:
            params = {"state": "all", "sort": "updated", "direction": "desc", "per_page": 20}
            if since:
                params["since"] = since

            resp = await client.get(f"{GITHUB_API}/repos/{repo}/pulls", params=params)
            if resp.status_code == 200:
                prs = resp.json()
                for pr in prs:
                    pr_id = f"github_pr_{repo.replace('/', '_')}_{pr['number']}"
                    pr_name = f"PR #{pr['number']}: {pr['title']}"

                    merge_entity(pr_id, "PullRequest", pr_name, source="github")
                    set_entity_attribute(pr_id, "url", pr["html_url"], "string", "github")
                    set_entity_attribute(pr_id, "state", pr["state"], "string", "github")
                    set_entity_attribute(pr_id, "number", str(pr["number"]), "int", "github")
                    set_entity_attribute(pr_id, "author", pr["user"]["login"], "string", "github")
                    set_entity_attribute(pr_id, "created_at", pr["created_at"], "datetime", "github")
                    set_entity_attribute(pr_id, "updated_at", pr["updated_at"], "datetime", "github")

                    if pr.get("merged_at"):
                        set_entity_attribute(pr_id, "merged_at", pr["merged_at"], "datetime", "github")

                    if pr.get("body"):
                        # Truncate body for graph storage
                        body = pr["body"][:500] if pr["body"] else ""
                        set_entity_attribute(pr_id, "description", body, "string", "github")

                    # Labels as attributes
                    labels = [l["name"] for l in pr.get("labels", [])]
                    if labels:
                        set_entity_attribute(pr_id, "labels", ",".join(labels), "string", "github")

                    # PR belongs to repo (INFORMATION edge)
                    try:
                        create_relationship(pr_id, repo_entity_id, "BELONGS_TO", "INFORMATION")
                    except Exception:
                        pass

                    link_entity_to_room(pr_id, room_id)
                    summary["pull_requests"] += 1
            else:
                summary["errors"].append(f"PRs: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            summary["errors"].append(f"PRs: {str(e)}")

        # --- Issues ---
        try:
            params = {"state": "all", "sort": "updated", "direction": "desc", "per_page": 20}
            if since:
                params["since"] = since

            resp = await client.get(f"{GITHUB_API}/repos/{repo}/issues", params=params)
            if resp.status_code == 200:
                issues = resp.json()
                for issue in issues:
                    # Skip PRs (GitHub API returns PRs in issues endpoint)
                    if issue.get("pull_request"):
                        continue

                    issue_id = f"github_issue_{repo.replace('/', '_')}_{issue['number']}"
                    issue_name = f"Issue #{issue['number']}: {issue['title']}"

                    merge_entity(issue_id, "Issue", issue_name, source="github")
                    set_entity_attribute(issue_id, "url", issue["html_url"], "string", "github")
                    set_entity_attribute(issue_id, "state", issue["state"], "string", "github")
                    set_entity_attribute(issue_id, "number", str(issue["number"]), "int", "github")
                    set_entity_attribute(issue_id, "author", issue["user"]["login"], "string", "github")
                    set_entity_attribute(issue_id, "created_at", issue["created_at"], "datetime", "github")

                    labels = [l["name"] for l in issue.get("labels", [])]
                    if labels:
                        set_entity_attribute(issue_id, "labels", ",".join(labels), "string", "github")

                    try:
                        create_relationship(issue_id, repo_entity_id, "BELONGS_TO", "INFORMATION")
                    except Exception:
                        pass

                    link_entity_to_room(issue_id, room_id)
                    summary["issues"] += 1
            else:
                summary["errors"].append(f"Issues: {resp.status_code}")
        except Exception as e:
            summary["errors"].append(f"Issues: {str(e)}")

        # --- Recent Commits (last 10) ---
        try:
            params = {"per_page": 10}
            if since:
                params["since"] = since

            resp = await client.get(f"{GITHUB_API}/repos/{repo}/commits", params=params)
            if resp.status_code == 200:
                commits = resp.json()
                for commit in commits:
                    sha_short = commit["sha"][:7]
                    commit_id = f"github_commit_{repo.replace('/', '_')}_{sha_short}"
                    commit_msg = commit["commit"]["message"].split("\n")[0][:100]
                    commit_name = f"{sha_short}: {commit_msg}"

                    merge_entity(commit_id, "Commit", commit_name, source="github")
                    set_entity_attribute(commit_id, "sha", commit["sha"], "string", "github")
                    set_entity_attribute(commit_id, "url", commit["html_url"], "string", "github")
                    set_entity_attribute(commit_id, "message", commit_msg, "string", "github")
                    set_entity_attribute(commit_id, "author", commit["commit"]["author"]["name"], "string", "github")
                    set_entity_attribute(commit_id, "date", commit["commit"]["author"]["date"], "datetime", "github")

                    try:
                        create_relationship(commit_id, repo_entity_id, "COMMITTED_TO", "INFORMATION")
                    except Exception:
                        pass

                    link_entity_to_room(commit_id, room_id)
                    summary["commits"] += 1
            else:
                summary["errors"].append(f"Commits: {resp.status_code}")
        except Exception as e:
            summary["errors"].append(f"Commits: {str(e)}")

        # --- Branches + per-branch file trees ---
        summary["files"] = 0
        summary["branches"] = 0

        CODE_EXTENSIONS = {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".h",
            ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".toml", ".md", ".txt",
            ".sql", ".sh", ".bash", ".dockerfile", ".env.example", ".gitignore",
            ".tf", ".hcl", ".proto", ".graphql", ".cypher",
        }
        SKIP_DIRS = {"node_modules/", ".git/", "vendor/", "dist/", "build/", "__pycache__/", ".next/"}

        try:
            # Get all branches
            resp = await client.get(f"{GITHUB_API}/repos/{repo}/branches", params={"per_page": 30})
            if resp.status_code == 200:
                branches = resp.json()
            else:
                branches = [{"name": "main", "commit": {"sha": "HEAD"}}]
                summary["errors"].append(f"Branches: {resp.status_code}, falling back to main")
        except Exception as e:
            branches = [{"name": "main", "commit": {"sha": "HEAD"}}]
            summary["errors"].append(f"Branches: {str(e)}")

        for branch_info in branches:
            branch_name = branch_info["name"]
            branch_sha = branch_info.get("commit", {}).get("sha", branch_name)

            # Create branch entity
            branch_entity_id = f"github_branch_{repo.replace('/', '_')}_{branch_name.replace('/', '_')}"
            merge_entity(branch_entity_id, "Branch", f"{repo}:{branch_name}", source="github")
            set_entity_attribute(branch_entity_id, "branch_name", branch_name, "string", "github")
            set_entity_attribute(branch_entity_id, "sha", branch_sha, "string", "github")
            set_entity_attribute(branch_entity_id, "url", f"https://github.com/{repo}/tree/{branch_name}", "string", "github")

            try:
                create_relationship(branch_entity_id, repo_entity_id, "BRANCH_OF", "INFORMATION")
            except Exception:
                pass

            link_entity_to_room(branch_entity_id, room_id)
            summary["branches"] += 1

            # Fetch file tree for this branch
            try:
                resp = await client.get(f"{GITHUB_API}/repos/{repo}/git/trees/{branch_sha}", params={"recursive": "1"})
                if resp.status_code != 200:
                    summary["errors"].append(f"Tree({branch_name}): {resp.status_code}")
                    continue

                tree = resp.json().get("tree", [])

                code_files = []
                for item in tree:
                    if item["type"] != "blob":
                        continue
                    path = item["path"]
                    if any(path.startswith(d) for d in SKIP_DIRS):
                        continue
                    if item.get("size", 0) > 50_000:
                        continue
                    ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
                    if ext.lower() in CODE_EXTENSIONS or path in (".gitignore", "Dockerfile", "Makefile", "README.md"):
                        code_files.append(item)

                # Fetch content — limit per branch to avoid rate limits
                max_per_branch = 30 if len(branches) <= 5 else 15
                for item in code_files[:max_per_branch]:
                    path = item["path"]
                    file_entity_id = f"github_file_{repo.replace('/', '_')}_{branch_name.replace('/', '_')}_{path.replace('/', '_').replace('.', '_')}"

                    display_name = f"{branch_name}:{path}"
                    merge_entity(file_entity_id, "File", display_name, source="github")
                    set_entity_attribute(file_entity_id, "path", path, "string", "github")
                    set_entity_attribute(file_entity_id, "branch", branch_name, "string", "github")
                    set_entity_attribute(file_entity_id, "sha", item["sha"], "string", "github")
                    set_entity_attribute(file_entity_id, "size", str(item.get("size", 0)), "int", "github")

                    # Fetch actual file content using Git Blobs API (reliable raw content)
                    try:
                        blob_sha = item["sha"]
                        file_resp = await client.get(
                            f"{GITHUB_API}/repos/{repo}/git/blobs/{blob_sha}",
                        )
                        if file_resp.status_code == 200:
                            blob_data = file_resp.json()
                            encoding = blob_data.get("encoding", "")
                            if encoding == "base64":
                                import base64
                                raw = blob_data.get("content", "")
                                content = base64.b64decode(raw).decode("utf-8", errors="replace")
                            else:
                                content = blob_data.get("content", "")
                            # Truncate to 10KB for graph storage
                            if len(content) > 10_000:
                                content = content[:10_000] + "\n\n... [truncated]"
                            set_entity_attribute(file_entity_id, "content", content, "string", "github")
                            print(f"  ✓ Stored content for {branch_name}:{path} ({len(content)} chars)")
                        else:
                            print(f"  ✗ Blob fetch failed for {path}: {file_resp.status_code} {file_resp.text[:100]}")
                            summary["errors"].append(f"Blob({path}): {file_resp.status_code}")
                    except Exception as e:
                        print(f"  ✗ Blob exception for {path}: {e}")
                        summary["errors"].append(f"Blob({path}): {str(e)}")

                    try:
                        create_relationship(file_entity_id, branch_entity_id, "FILE_IN", "RESOURCE")
                    except Exception:
                        pass

                    try:
                        create_relationship(file_entity_id, repo_entity_id, "FILE_IN", "RESOURCE")
                    except Exception:
                        pass

                    link_entity_to_room(file_entity_id, room_id)
                    summary["files"] += 1

            except Exception as e:
                summary["errors"].append(f"Tree({branch_name}): {str(e)}")

    # Audit the sync
    audit(user_id, "connector_synced", room_id, "github", repo_entity_id, {
        "repo": repo,
        "prs": summary["pull_requests"],
        "issues": summary["issues"],
        "commits": summary["commits"],
        "branches": summary["branches"],
        "files": summary["files"],
    })

    return summary
