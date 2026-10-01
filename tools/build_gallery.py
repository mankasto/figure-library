from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps
import argparse, hashlib, json, sys
parser = argparse.ArgumentParser(description="Build the gallery from local figure-library data and originals")
parser.add_argument('--source-root', type=Path, required=True)
parser.add_argument('--html-only', action='store_true', help='Reuse existing compressed images')
args = parser.parse_args()
root = args.source_root.resolve()
out = Path(__file__).resolve().parents[1]
(out / 'images').mkdir(parents=True, exist_ok=True)
(out / 'thumbs').mkdir(parents=True, exist_ok=True)
source_html = (root / 'gallery.html').read_text()
html = (out / 'tools' / 'gallery_template.html').read_text()
for name, placeholder in [('D', '/*__DATA__*/[]'), ('CN', '/*__CATCN__*/{}'), ('SUB', '/*__SUBCN__*/{}')]:
    value, _ = json.JSONDecoder().raw_decode(source_html.split('const ' + name + '=', 1)[1])
    html = html.replace(placeholder, json.dumps(value, ensure_ascii=False))
tail = html.split('const D=', 1)[1]
rows, end = json.JSONDecoder().raw_decode(tail)
def convert(row):
    row = dict(row)
    src = root / row['path']
    assert src.resolve().is_relative_to(root.resolve()) and src.is_file(), src
    key = hashlib.sha256(row['path'].encode()).hexdigest()[:20] + '.webp'
    if not args.html_only or not all((out / folder / key).is_file() for folder in ['images','thumbs']):
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((1600,1600), Image.Resampling.LANCZOS)
            im.save(out / 'images' / key, 'WEBP', quality=80, method=4)
            im.thumbnail((600,600), Image.Resampling.LANCZOS)
            im.save(out / 'thumbs' / key, 'WEBP', quality=75, method=4)
    row['path'] = 'images/' + key
    row['thumb'] = 'thumbs/' + key
    row['original'] = ''
    return row
with ThreadPoolExecutor(max_workers=8) as pool:
    rows = list(pool.map(convert, rows))
html = html.split('const D=',1)[0] + 'const D=' + json.dumps(rows, ensure_ascii=False, separators=(',',':')) + tail[end:]
html = html.replace('R.slice(0,1500).map', 'R.map')
html = html.replace('loading="lazy" src="${encodeURI(r.path)}"', 'loading="lazy" decoding="async" src="${encodeURI(r.thumb)}"')
html = html.replace('<h1>论文图素材库</h1>', '<h1>论文图素材库</h1><span style="color:var(--mute);font-size:12px">图片为压缩预览，原图请查看论文链接</span>')
backend = root / '_share' / 'vote-backend'
if (backend / 'public-config.json').is_file():
    config = json.loads((backend / 'public-config.json').read_text())
    ids = sorted({r['id'] for r in rows})
    assert len(ids) == len(rows), 'Figure IDs must be unique'
    (backend / 'catalog.json').write_text(json.dumps(ids))
    (out / 'vote-config.js').write_text('window.FIGLIB_VOTE_API = ' + json.dumps(config['api']) + ';\nwindow.FIGLIB_BOARD_THRESHOLD = ' + str(config.get('boardThreshold', 2)) + ';\n')
    config_version = hashlib.sha256((out / 'vote-config.js').read_bytes()).hexdigest()[:12]
    client_version = hashlib.sha256((out / 'shared-votes.js').read_bytes()).hexdigest()[:12]
    html = html.replace('</body>', f'<script src="vote-config.js?v={config_version}"></script><script src="shared-votes.js?v={client_version}"></script></body>')
    print('Shared voting enabled. Deploy vote-backend when new figure IDs are added.')
for name in ['index.html','gallery.html']:
    (out / name).write_text(html)
(out / '.nojekyll').touch()
print(json.dumps({'figures':len(rows),'output':str(out),'MB':round(sum(f.stat().st_size for f in out.rglob('*') if f.is_file() and '.git' not in f.parts)/1e6,2)},ensure_ascii=False))
