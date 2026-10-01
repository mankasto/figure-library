"""Regression: stale local HTML/client must not overwrite the checked-in UI."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

REPO = Path(__file__).resolve().parents[1]


class BuildGalleryTest(unittest.TestCase):
    def test_stale_local_sources_and_repeat_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'library'
            repo = Path(temp) / 'repo'
            (root / '_share/vote-backend').mkdir(parents=True)
            (repo / 'tools').mkdir(parents=True)
            for name in ('build_gallery.py', 'gallery_template.html'):
                shutil.copy2(REPO / 'tools' / name, repo / 'tools' / name)
            shutil.copy2(REPO / 'shared-votes.js', repo / 'shared-votes.js')
            Image.new('RGB', (1800, 900), 'white').save(root / 'figure.png')
            row = {'id': 'stable-figure-id', 'path': 'figure.png', 'arxiv': '2508.19236'}
            # Deliberately obsolete local page and vote client.
            (root / 'gallery.html').write_text('const D=' + json.dumps([row]) + ';const CN={};const SUB={};OLD_UI')
            backend = root / '_share/vote-backend'
            (backend / 'shared-votes.js').write_text('OLD_CLIENT')
            (backend / 'public-config.json').write_text(json.dumps({'api': 'https://example.invalid', 'boardThreshold': 1}))
            command = [sys.executable, str(repo / 'tools/build_gallery.py'), '--source-root', str(root)]
            subprocess.run(command, check=True, capture_output=True)
            first = (repo / 'index.html').read_bytes()
            html = first.decode()
            self.assertIn('id="years"', html)
            self.assertIn('years.has(arxivYear(r.arxiv))', html)
            self.assertNotIn('OLD_UI', html)
            self.assertEqual((repo / 'shared-votes.js').read_bytes(), (REPO / 'shared-votes.js').read_bytes())
            self.assertIn('selectAllYears(true)', (repo / 'shared-votes.js').read_text())
            rows, _ = json.JSONDecoder().raw_decode(html.split('const D=', 1)[1])
            self.assertEqual(rows[0]['id'], row['id'])
            self.assertEqual(json.loads((backend / 'catalog.json').read_text()), [row['id']])
            for field, size in [('path', (1600, 800)), ('thumb', (600, 300))]:
                with Image.open(repo / rows[0][field]) as image:
                    self.assertEqual(image.size, size)
            mtimes = {p: p.stat().st_mtime_ns for p in repo.glob('*/*.webp')}
            subprocess.run(command + ['--html-only'], check=True, capture_output=True)
            self.assertEqual(first, (repo / 'index.html').read_bytes())
            self.assertEqual(first, (repo / 'gallery.html').read_bytes())
            self.assertEqual(mtimes, {p: p.stat().st_mtime_ns for p in mtimes})


if __name__ == '__main__':
    unittest.main()
