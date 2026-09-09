#!/usr/bin/env python3
"""Rebuild the Reveal.js deck from topic-00-slides.md."""
import html
import json
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parent
runtime = Path.home() / '.local/share/md-to-pdf'

def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True, **kw).stdout

slides = []
notes = ['# Chapter 0 Speaker Notes\n']
for number, chunk in enumerate(re.split(r'\n---\n', (root / 'topic-00-slides.md').read_text()), 1):
    body, _, note = chunk.partition('\nNote:\n')
    title = re.search(r'^#+ (.+)', body.strip()).group(1)
    notes.append(f'## {title}\n\n{note.strip()}\n')
    def diagram(match):
        path = root / 'slide-assets' / f'diagram-{number:02d}.mmd'
        path.write_text(match.group(1))
        run(['/opt/homebrew/bin/node', runtime / 'node_modules/@mermaid-js/mermaid-cli/src/cli.js',
             '-i', path, '-o', path.with_suffix('.svg'), '-c', runtime / 'mermaid.json',
             '-p', runtime / 'puppeteer.json', '-b', 'transparent'])
        return f'![{title}](slide-assets/{path.stem}.svg)'
    body = re.sub(r'```mermaid\n(.*?)\n```', diagram, body, flags=re.S)
    content = run(['/opt/homebrew/bin/pandoc', '-f', 'markdown-implicit_figures', '-t', 'html5'], input=body)
    slides.append(f'<section>{content}<aside class="notes">{html.escape(note.strip())}</aside></section>')
page = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chapter 0: Why Use Databases?</title>
<link rel="stylesheet" href="slide-assets/reveal.css">
<link rel="stylesheet" href="slide-assets/slides.css">
</head><body><div class="reveal"><div class="slides">'''+ '\n'.join(slides)+'''</div></div>
<script src="slide-assets/reveal.js"></script><script src="slide-assets/notes.js"></script>
<script>Reveal.initialize({width:1280,height:720,margin:0.05,center:true,hash:true,slideNumber:true,transition:'none',plugins:[RevealNotes]});</script>
</body></html>'''
(root / 'topic-00-slides.html').write_text(page)
(root / 'topic-00-speaker-notes.md').write_text('\n'.join(notes))
print(f'Built {len(slides)} slides.')
