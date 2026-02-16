#!/usr/bin/env python3
"""
Script to create GitHub issues from ISSUES.md file.

Usage:
    export GITHUB_TOKEN=your_token_here
    python3 create_issues.py
"""

import os
import sys
import re
import requests
import time

REPO_OWNER = "NDemchishin"
REPO_NAME = "watch-service-platform"
ISSUES_FILE = "ISSUES.md"

# Label definitions
LABELS_TO_CREATE = {
    "bug": {"color": "d73a4a", "description": "Something isn't working"},
    "test": {"color": "0e8a16", "description": "Test coverage"},
    "enhancement": {"color": "a2eeef", "description": "New feature or request"},
    "sprint-3-fix": {"color": "fbca04", "description": "Sprint 3 bugfix"},
    "sprint-4": {"color": "c5def5", "description": "Sprint 4 feature"},
    "sprint-5": {"color": "bfdadc", "description": "Sprint 5 feature"},
    "sprint-6": {"color": "d4c5f9", "description": "Sprint 6 feature"},
    "infra": {"color": "0052cc", "description": "Infrastructure and tooling"},
}


def get_token():
    """Get GitHub token from environment."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        print("\nUsage:")
        print("  export GITHUB_TOKEN=ghp_your_token_here")
        print("  python3 create_issues.py")
        sys.exit(1)
    return token


def create_label(token, label_name, color, description):
    """Create a label in the repository."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/labels"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    data = {
        "name": label_name,
        "color": color,
        "description": description,
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print(f"✓ Created label: {label_name}")
    elif response.status_code == 422:
        # Label already exists
        print(f"→ Label already exists: {label_name}")
    else:
        print(f"⚠ Failed to create label {label_name}: {response.status_code}")
        print(f"  {response.json()}")


def parse_issues_from_md(file_path):
    """Parse issues from ISSUES.md file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []

    # Split by issue headers (### Issue #N)
    issue_blocks = re.split(r'\n### Issue #(\d+) — (.+?)\n', content)

    # issue_blocks[0] is intro text, then triplets: (number, title, body)
    for i in range(1, len(issue_blocks), 3):
        if i + 2 > len(issue_blocks):
            break

        issue_num = issue_blocks[i]
        title = issue_blocks[i + 1]
        body = issue_blocks[i + 2].strip()

        # Extract labels from title (e.g., [bug][sprint-3-fix])
        labels_match = re.findall(r'\[([^\]]+)\]', title)
        labels = labels_match if labels_match else []

        # Remove label tags from title
        clean_title = re.sub(r'\[([^\]]+)\]\s*', '', title).strip()

        # Stop at next section or end
        next_section = re.search(r'\n## ', body)
        if next_section:
            body = body[:next_section.start()].strip()

        # Remove the horizontal rule at the end
        body = re.sub(r'\n---\s*$', '', body).strip()

        issues.append({
            'number': int(issue_num),
            'title': clean_title,
            'body': body,
            'labels': labels,
        })

    return issues


def create_issue(token, title, body, labels):
    """Create a GitHub issue."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    data = {
        "title": title,
        "body": body,
        "labels": labels,
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        issue_data = response.json()
        return issue_data['number'], issue_data['html_url']
    else:
        print(f"❌ Failed to create issue: {response.status_code}")
        print(f"   {response.json()}")
        return None, None


def main():
    """Main function."""
    print("🚀 GitHub Issues Creator for Watch Service Platform\n")

    # Get token
    token = get_token()

    # Test authentication
    print("🔐 Testing authentication...")
    test_url = "https://api.github.com/user"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    response = requests.get(test_url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        print(f"   {response.json()}")
        sys.exit(1)

    user = response.json()
    print(f"✓ Authenticated as: {user['login']}\n")

    # Create labels
    print("🏷️  Creating labels...")
    for label_name, label_info in LABELS_TO_CREATE.items():
        create_label(token, label_name, label_info['color'], label_info['description'])
    print()

    # Parse issues
    print("📖 Parsing ISSUES.md...")
    if not os.path.exists(ISSUES_FILE):
        print(f"❌ Error: {ISSUES_FILE} not found")
        sys.exit(1)

    issues = parse_issues_from_md(ISSUES_FILE)
    print(f"✓ Found {len(issues)} issues\n")

    # Create issues
    print("📝 Creating issues...")
    created_count = 0

    for issue in issues:
        print(f"   Creating issue #{issue['number']}: {issue['title'][:60]}...")

        issue_num, issue_url = create_issue(
            token,
            f"#{issue['number']} — {issue['title']}",
            issue['body'],
            issue['labels']
        )

        if issue_num:
            print(f"   ✓ Created: {issue_url}")
            created_count += 1
        else:
            print(f"   ⚠ Failed to create issue #{issue['number']}")

        # Rate limiting: sleep between requests
        time.sleep(0.5)

    print(f"\n✅ Done! Created {created_count}/{len(issues)} issues")
    print(f"\nView all issues: https://github.com/{REPO_OWNER}/{REPO_NAME}/issues")


if __name__ == "__main__":
    main()
