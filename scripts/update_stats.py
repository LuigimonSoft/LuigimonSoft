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
    width, height = 400, 350
    elements = [
        '<rect x="1" y="1" width="398" height="348" rx="12" fill="#161b22" stroke="#30363d"/>',
        f'<text x="24" y="38" class="title">{html.escape(title)}</text>',
    ]
    if title == 'Most Used Languages':
        colors = ['#f34b7d', '#f1e05a', '#dea584', '#3178c6', '#3572a5', '#f05138', '#a074c4', '#563d7c']
        for i, line in enumerate(lines):
            label, _, value = line.rpartition(': ')
            try:
                percentage = float(value.rstrip('%'))
            except ValueError:
                elements.append(f'<text x="24" y="75" class="row">{html.escape(line)}</text>')
                break
            y = 72 + i * 33
            elements.append(f'<text x="24" y="{y}" class="row">{html.escape(label)}</text>')
            elements.append(f'<text x="376" y="{y}" text-anchor="end" class="row">{html.escape(value)}</text>')
            elements.append(f'<rect x="24" y="{y + 8}" width="352" height="6" rx="3" fill="#30363d"/>')
            elements.append(f'<rect x="24" y="{y + 8}" width="{352 * percentage / 100:.1f}" height="6" rx="3" fill="{colors[i % len(colors)]}"/>')
    else:
        for i, line in enumerate(lines):
            label, _, value = line.rpartition(': ')
            y = 88 + i * 75
            elements.append(f'<text x="24" y="{y}" class="row">{html.escape(label)}</text>')
            elements.append(f'<text x="24" y="{y + 31}" class="value">{html.escape(value)}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">'
            '<style>.title{font:600 20px sans-serif;fill:#58a6ff}.row{font:14px sans-serif;fill:#c9d1d9}.value{font:600 23px sans-serif;fill:#f0f6fc}</style>'
            + ''.join(elements) + '</svg>\n')


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
