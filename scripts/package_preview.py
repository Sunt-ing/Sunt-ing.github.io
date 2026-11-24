"""Create an offline single-file preview and a source archive beside the checkout."""
from pathlib import Path
import json,re,subprocess
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
pages={}
for p in [ROOT/'index.html',*(ROOT/'zh').rglob('index.html'),*(ROOT/'en').rglob('index.html')]:
 key='/' if p==ROOT/'index.html' else '/'+str(p.parent.relative_to(ROOT))+'/'
 s=p.read_text()
 s=re.sub(r'<link rel="stylesheet" href="(/assets/[^" ]+)">',lambda m:'<style>'+(ROOT/m[1].lstrip('/')).read_text()+'</style>',s)
 js=(ROOT/'assets/blog.js').read_text().replace('(() => {','document.addEventListener("DOMContentLoaded", () => {',1).replace('})();','});')
 s=s.replace('<script defer src="/assets/blog.js"></script>','<script>'+js+'</script>')
 s=s.replace('</body>', '<script>'+ (ROOT/'scripts/preview-frame.js').read_text() +'</script></body>')
 pages[key]=s
payload=json.dumps(pages,ensure_ascii=False).replace('</','<\\/')
preview='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ting Sun · 主页与双语博客预览</title><style>html,body,iframe{width:100%;height:100%;margin:0;border:0;display:block}</style><iframe title="主页与博客预览" sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe><script>const pages='''+payload+';'+(ROOT/'scripts/preview-shell.js').read_text()+'</script></html>'
(ROOT.parent/'bilingual-blog-preview.html').write_text(preview)
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
with ZipFile(ROOT.parent/'ting-sun-bilingual-blog.zip','w',ZIP_DEFLATED) as z:
 for name in sorted(set(files)):z.write(ROOT/name,'site/'+name)
 z.write(ROOT.parent/'bilingual-blog-preview.html','preview.html')
print('Updated homepage-first preview and source archive.')
