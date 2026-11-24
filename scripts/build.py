#!/usr/bin/env python3
"""Build committed static pages from bilingual Markdown. Run from any directory."""
import html, json, re, math
from pathlib import Path
import markdown
from navigation import navigation
ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sunt-ing.github.io'
POSTS = json.loads((ROOT/'content/posts.json').read_text())
E = html.escape
THEME = "(()=>{let theme='light';try{const saved=localStorage.getItem('ting-theme');if(saved==='dark'||saved==='light')theme=saved}catch{}document.documentElement.dataset.theme=theme})()"

def shell(lang, title, description, path, alternate, body):
    zh = lang == 'zh'
    return f'''<!doctype html>
<html lang="{'zh-CN' if zh else 'en'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · Ting Sun</title><meta name="description" content="{E(description,quote=True)}">
<link rel="canonical" href="{BASE}{path}"><link rel="alternate" hreflang="{'en' if zh else 'zh-CN'}" href="{BASE}{alternate}"><link rel="alternate" hreflang="{'zh-CN' if zh else 'en'}" href="{BASE}{path}">
<meta property="og:title" content="{E(title,quote=True)}"><meta property="og:description" content="{E(description,quote=True)}"><meta property="og:url" content="{BASE}{path}"><meta property="og:type" content="{'article' if '/p/' in path else 'website'}"><meta name="color-scheme" content="light dark">
<script>{THEME}</script><link rel="stylesheet" href="/assets/blog.css"><script defer src="/assets/blog.js"></script></head>
<body id="top"><a class="skip" href="#main">{'跳到正文' if zh else 'Skip to content'}</a>
<header class="site-header"><div class="header-inner"><a class="brand" href="/">Ting Sun <span lang="zh-CN">孙挺</span></a>{navigation(lang, 'writing')}<div class="controls"><nav class="languages" aria-label="Language"><a lang="en" hreflang="en" href="{alternate if zh else path}" {'aria-current="page"' if not zh else ''}>EN</a><a lang="zh-CN" hreflang="zh-CN" href="{path if zh else alternate}" {'aria-current="page"' if zh else ''}>中</a></nav><button class="theme" aria-label="{'切换深浅色主题' if zh else 'Toggle dark theme'}" aria-pressed="false">◐</button></div></div></header>
{body}
<footer class="site-footer"><span>© Ting Sun · 孙挺</span><span><a href="https://www.zhihu.com/people/sunt-ing">知乎</a> · <a href="https://github.com/Sunt-ing">GitHub</a> · <a href="mailto:suntcrick@gmail.com">Email</a></span></footer></body></html>'''

def write(path, text):
    p = ROOT/path.lstrip('/')/'index.html'
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text)

homepage = ROOT/'index.html'
home_html = re.sub(r'<nav class="main-nav".*?</nav>', navigation('en', 'home'), homepage.read_text(), count=1)
home_html = re.sub(r'<script>.*?</script>', '<script>'+THEME+'</script>', home_html, count=1)
latest = []
for post in POSTS[:3]:
    meta = post['en']
    slug = post['slug']
    latest.append(f'<article class="writing-entry"><div class="eyebrow">{E(meta["category"])}</div><h3><a href="/en/p/{slug}/">{E(meta["title"])}</a></h3><p>{E(meta["description"])}</p><div class="paper-footer"><a href="/en/p/{slug}/">English</a><a href="/zh/p/{slug}/" lang="zh-CN">中文</a></div></article>')
home_writing = '<section class="home-section home-writing" id="writing" aria-labelledby="writing-title"><div class="section-heading"><h2 id="writing-title">TingLog <span lang="zh-CN">技术文章</span></h2><a href="/en/blog/">All posts</a></div>'+''.join(latest)+'</section>'
home_html = re.sub(r'<section class="home-section home-writing".*?</section>', home_writing, home_html, count=1, flags=re.S)
homepage.write_text(home_html)
urls = ['/']
for lang in ('zh','en'):
    zh=lang=='zh'; other='en' if zh else 'zh'
    cards=[]
    for post in POSTS:
        meta=post[lang]; slug=post['slug']; path=f'/{lang}/p/{slug}/'; alternate=f'/{other}/p/{slug}/'
        text=(ROOT/f'content/{slug}/{lang}.md').read_text()
        text=re.sub(r'^# [^\n]+\n+', '', text)
        md=markdown.Markdown(extensions=['toc','tables','fenced_code'],extension_configs={'toc':{'permalink':False}})
        rendered=md.convert(text)
        count=len(re.findall(r'[\u4e00-\u9fff]',text))+len(re.findall(r'[A-Za-z]+',text)) if zh else len(text.split())
        minutes=max(1,math.ceil(count/(450 if zh else 230)))
        timing=f'约 {minutes} 分钟' if zh else f'{minutes} min read'
        toc_label='目录' if zh else 'On this page'
        source_label='知乎原文' if zh else 'Original on Zhihu'
        toc=md.toc
        subject = ' / '+E(post['subject']) if post.get('subject') else ''
        date=f'<time datetime="{post["date"]}">{post["date"]}</time>' if post.get('date') else ''
        body=f'''<div class="layout"><aside class="sidebar" aria-label="{toc_label}"><div class="eyebrow">{toc_label}</div>{toc}<div class="side-bottom"><a href="{post['source']}">{source_label} ↗</a><a href="/{lang}/blog/">← {'所有文章' if zh else 'All posts'}</a></div></aside><main id="main"><article><header class="post-header"><div class="eyebrow">{E(meta['category'])}{subject}</div><h1>{E(meta['title'])}</h1><p class="post-subtitle">{E(meta['description'])}</p><div class="meta"><span>Ting Sun · 孙挺</span>{date}<span>{timing}</span><a href="{post['source']}">{source_label}</a><a href="{alternate}">{'Read in English' if zh else '阅读中文版'}</a></div></header><details class="mobile-toc"><summary>{toc_label}</summary>{toc}</details><div class="prose">{rendered}</div></article><div class="back-top"><a href="#top">↑ {'回到顶部' if zh else 'Back to top'}</a></div></main></div>'''
        write(path,shell(lang,meta['title'],meta['description'],path,alternate,body)); urls.append(path)
        cards.append(f'''<article class="post-card"><div class="eyebrow">{E(meta['category'])}</div><h2><a href="{path}">{E(meta['title'])}</a></h2><p>{E(meta['description'])}</p><div class="meta"><span>{timing}</span><a href="{path}">{'阅读全文' if zh else 'Read article'} →</a><a href="{alternate}">{'English' if zh else '中文'}</a></div></article>''')
    title='TingLog'
    desc='关于大模型架构、训练与系统的技术笔记。' if zh else 'Notes on model architectures, training, and systems.'
    path=f'/{lang}/blog/'; alternate=f'/{other}/blog/'
    body=f'<main class="index" id="main"><div class="eyebrow">TINGLOG / NOTES</div><h1>{title}</h1><p class="index-intro">{desc}</p>{"".join(cards)}</main>'
    write(path,shell(lang,title,desc,path,alternate,body)); urls.append(path)
(ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE}{p}</loc></url>' for p in urls)+'</urlset>\n')
(ROOT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
(ROOT/'.nojekyll').touch()
print(f'Built {len(urls)-1} bilingual pages.')
