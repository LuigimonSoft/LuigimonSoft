#!/usr/bin/env python3
"""Generate profile cards from public GitHub API data."""
import hashlib
import html
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

USER = 'LuigimonSoft'
API = 'https://api.github.com'
OUT = Path('assets/stats')
HEADERS = {'Accept': 'application/vnd.github+json', 'User-Agent': 'LuigimonSoft-profile-stats'}
if os.environ.get('GITHUB_TOKEN'):
    HEADERS['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']


def get(path):
    with urlopen(Request(API + path, headers=HEADERS), timeout=30) as response:
        return json.load(response)


def card(title, lines):
    height = 70 + 30 * len(lines)
    rows = ''.join(f'<text x="24" y="{72 + i * 30}" class="row">{html.escape(line)}</text>' for i, line in enumerate(lines))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="{height}" viewBox="0 0 400 {height}" role="img" aria-label="{html.escape(title)}">'
            '<style>.title{font:600 20px sans-serif;fill:#58a6ff}.row{font:15px sans-serif;fill:#8b949e}</style>'
            f'<text x="24" y="35" class="title">{html.escape(title)}</text>{rows}</svg>\n')


def main():
    user = get('/users/' + USER)
    repos = []
    page = 1
    while True:
        batch = get(f'/users/{USER}/repos?per_page=100&page={page}&type=owner')
        repos.extend(repo for repo in batch if not repo['fork'])
        if len(batch) < 100:
            break
        page += 1
    languages = {}
    for repo in repos:
        for name, count in get(f"/repos/{USER}/{repo['name']}/languages").items():
            languages[name] = languages.get(name, 0) + count
    total = sum(languages.values())
    top = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:8]
    overview = [f"Public repositories: {user['public_repos']}",
                f"Stars on original repositories: {sum(repo['stargazers_count'] for repo in repos)}",
                f"Followers: {user['followers']}"]
    language_lines = [f'{name}: {count / total * 100:.1f}%' for name, count in top] if total else ['No language data available']
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'overview.svg').write_text(card('GitHub Stats', overview), encoding='utf-8')
    (OUT / 'languages.svg').write_text(card('Most Used Languages', language_lines), encoding='utf-8')
    update_image_urls()


def update_image_urls():
    # GitHub caches proxied images by URL, so change the URL when a card changes.
    readme = Path('README.md')
    content = readme.read_text(encoding='utf-8')
    for name in ('overview', 'languages'):
        digest = hashlib.sha256((OUT / f'{name}.svg').read_bytes()).hexdigest()[:12]
        base = f'https://raw.githubusercontent.com/{USER}/{USER}/master/assets/stats/{name}.svg'
        content, count = re.subn(re.escape(base) + r'(?:\?v=[a-f0-9]+)?', f'{base}?v={digest}', content)
        if count != 1:
            raise ValueError(f'Expected exactly one README URL for {name}, found {count}')
    readme.write_text(content, encoding='utf-8')


if __name__ == '__main__':
    main()
