"""Fetch pinned, local-only reference STA dependencies; no system installation."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'study/tools/stream_sta'
OPENROAD_REVISION = '64939f3717ad7c694199ba04cb98924b98022868'
LIB_SHA256 = '8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'FlexTransform-research'}), timeout=120) as f:
        return f.read()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest_path = DEST / 'manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for item in manifest['files']:
            assert hashlib.sha256((DEST/item['file']).read_bytes()).hexdigest() == item['sha256']
        print(manifest_path)
        return
    revision = OPENROAD_REVISION
    lib_url = f'https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/{revision}/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
    deb_url = 'https://archive.ubuntu.com/ubuntu/pool/universe/o/opensta/opensta_0~20191111gitc018cb2+dfsg-1.1_amd64.deb'
    entries = []
    for name, url, expected in (
        ('NangateOpenCellLibrary_typical.lib', lib_url, LIB_SHA256),
        ('opensta.deb', deb_url, '9ec29cc74cc66cd82e6fa85aad2d3897c6315aa26adbc380892416e7a5e87a1b')):
        data = fetch(url)
        digest = hashlib.sha256(data).hexdigest()
        if expected:
            assert digest == expected
        (DEST/name).write_bytes(data)
        entries.append({'file': name, 'url': url, 'sha256': digest})
        print(name, len(data), digest, flush=True)
    manifest = {'openroad_flow_scripts_commit': revision, 'files': entries}
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
