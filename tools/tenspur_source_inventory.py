#!/usr/bin/env python3
"""TenSpur source inventory: read-only extraction for developer handover.
Outputs JSON + Markdown without reading secret values."""
from __future__ import annotations
import argparse, ast, json, os, re, tomllib
from pathlib import Path
from collections import Counter
try:
    import yaml
except Exception:
    yaml=None

SKIP={'.git','node_modules','dist','build','__pycache__','.pytest_cache','.mypy_cache','.vite','backups','input','import-evidence','certs','data','uploads'}
TEXT_EXT={'.py','.ts','.tsx','.js','.mjs','.cjs','.vue','.css','.scss','.html','.md','.toml','.json','.yml','.yaml','.ini','.conf','.sh','.sql'}

def rel(p,root): return p.relative_to(root).as_posix()
def safe_text(p):
    try: return p.read_text('utf-8',errors='replace')
    except Exception: return ''
def files(root):
    for dp,dn,fn in os.walk(root):
        dn[:]=sorted(d for d in dn if d not in SKIP and not d.startswith('.venv'))
        for n in sorted(fn):
            p=Path(dp)/n
            if p.suffix.lower() in TEXT_EXT or n in {'Dockerfile','Makefile'}: yield p

def version_data(root):
    out={}
    for p in files(root):
        r=rel(p,root)
        if p.name=='package.json':
            try:
                d=json.loads(safe_text(p)); out[r]={'name':d.get('name'),'version':d.get('version'),'dependencies':d.get('dependencies',{}),'devDependencies':d.get('devDependencies',{}),'scripts':d.get('scripts',{})}
            except Exception as e: out[r]={'error':str(e)}
        elif p.name=='pyproject.toml':
            try:
                d=tomllib.loads(safe_text(p)); proj=d.get('project',{})
                out[r]={'requires_python':proj.get('requires-python'),'dependencies':proj.get('dependencies',[]),'optional_dependencies':proj.get('optional-dependencies',{})}
            except Exception as e: out[r]={'error':str(e)}
    return out

def route_data(root):
    out=[]
    for p in files(root):
        if p.suffix!='.py': continue
        t=safe_text(p); prefix=''
        pm=re.search(r'APIRouter\s*\([^)]*prefix\s*=\s*["\']([^"\']*)',t,re.S)
        if pm: prefix=pm.group(1)
        for m in re.finditer(r'@(?P<obj>[\w.]+)\.(?P<meth>get|post|put|patch|delete|options|head)\s*\(\s*["\'](?P<path>[^"\']*)["\'](?P<args>.*?)\)\s*\n\s*(?:async\s+)?def\s+(?P<fn>\w+)',t,re.S|re.I):
            args=m.group('args'); deps=sorted(set(re.findall(r'(?:Depends|Security)\s*\(\s*([\w.]+)',args)))
            out.append({'file':rel(p,root),'router':m.group('obj'),'method':m.group('meth').upper(),'declared_path':m.group('path'),'router_prefix':prefix,'path':prefix+m.group('path'),'function':m.group('fn'),'dependencies':deps})
    return out

def vue_data(root):
    out=[]
    for p in files(root):
        if p.suffix!='.vue': continue
        t=safe_text(p); name=p.stem
        nm=re.search(r'defineOptions\s*\(\s*\{[^}]*name\s*:\s*["\']([^"\']+)',t,re.S)
        if nm:name=nm.group(1)
        props=[]; events=[]; state=[]
        for pat in [r'defineProps\s*<([^>]+)>',r'defineProps\s*\(\s*\{(.*?)\}\s*\)']:
            m=re.search(pat,t,re.S)
            if m: props=sorted(set(re.findall(r'(?m)^\s*([A-Za-z_$][\w$]*)\??\s*:',m.group(1)))); break
        m=re.search(r'defineEmits\s*<(.+?)>\s*\(',t,re.S)
        if m:
            block=m.group(1)
            events=sorted(set(re.findall(r'["\']([^"\']+)["\']',block)) | set(re.findall(r'\(\s*(?:e|event)\s*:\s*["\']([^"\']+)["\']',block)))
        if not events:
            m=re.search(r'defineEmits\s*\(\s*\[([^]]*)\]',t,re.S)
            if m: events=sorted(set(re.findall(r'["\']([^"\']+)["\']',m.group(1))))
        events=sorted(set(events) | set(re.findall(r'emit\s*\(\s*["\']([^"\']+)["\']',t)))
        state=sorted(set(re.findall(r'(?m)^\s*(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:ref|reactive|computed)\s*\(',t)))
        imports=sorted(set(re.findall(r'import\s+([A-Z][\w$]*)\s+from\s+["\']([^"\']+\.vue)["\']',t)))
        css_media=sorted(set(re.findall(r'@media\s*\(([^)]+)\)',t)))
        out.append({'file':rel(p,root),'name':name,'lines':t.count('\n')+1,'props':props,'events':events,'state':state,'vue_imports':[{'name':a,'from':b} for a,b in imports],'media_queries':css_media})
    return out

def migrations(root):
    out=[]
    for p in files(root):
        if p.suffix!='.py' or not ('alembic' in rel(p,root).lower() or 'migration' in rel(p,root).lower()): continue
        t=safe_text(p)
        rev=re.search(r'(?m)^revision(?:\s*:\s*[^=]+)?\s*=\s*["\']([^"\']+)',t)
        down=re.search(r'(?m)^down_revision(?:\s*:\s*[^=]+)?\s*=\s*(?:["\']([^"\']+)["\']|None)',t)
        if rev: out.append({'file':rel(p,root),'revision':rev.group(1),'down_revision':down.group(1) if down and down.group(1) else None,'title':next((x.strip('# ') for x in t.splitlines()[:8] if x.strip() and not x.strip().startswith(('"""',"'''"))),p.stem)})
    return sorted(out,key=lambda x:x['file'])

def compose_data(root):
    out=[]
    for p in files(root):
        if p.name not in {'docker-compose.yml','docker-compose.yaml','compose.yml','compose.yaml'}: continue
        try:
            d=yaml.safe_load(safe_text(p)) if yaml else {}; sv=[]
            for n,v in (d.get('services') or {}).items():
                sv.append({'name':n,'image':v.get('image'),'build':v.get('build'),'ports':v.get('ports',[]),'volumes':v.get('volumes',[]),'networks':v.get('networks',[])})
            out.append({'file':rel(p,root),'services':sv,'volumes':sorted((d.get('volumes') or {}).keys()),'networks':sorted((d.get('networks') or {}).keys())})
        except Exception as e: out.append({'file':rel(p,root),'error':str(e)})
    return out

def py_symbols(root):
    mods=[]
    for p in files(root):
        if p.suffix!='.py':continue
        t=safe_text(p)
        try:
            tree=ast.parse(t); classes=[n.name for n in tree.body if isinstance(n,ast.ClassDef)]; funcs=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        except Exception: classes=[];funcs=[]
        mods.append({'file':rel(p,root),'lines':t.count('\n')+1,'classes':classes,'functions':funcs})
    return mods

def tree_lines(root):
    allf=[rel(p,root) for p in files(root)]
    return sorted(allf)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root');ap.add_argument('--out',required=True);ap.add_argument('--label',default='TenSpur');a=ap.parse_args()
    root=Path(a.root).resolve(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    fs=tree_lines(root); inv={'label':a.label,'root_display':root.name,'files':fs,'counts':dict(Counter(Path(x).suffix or Path(x).name for x in fs)),'dependencies':version_data(root),'python_modules':py_symbols(root),'fastapi_routes':route_data(root),'vue_components':vue_data(root),'migrations':migrations(root),'compose':compose_data(root)}
    inv['summary']={'source_files':len(fs),'python_files':sum(x.endswith('.py') for x in fs),'ts_files':sum(x.endswith(('.ts','.tsx')) for x in fs),'vue_files':sum(x.endswith('.vue') for x in fs),'routes':len(inv['fastapi_routes']),'components':len(inv['vue_components']),'migrations':len(inv['migrations']),'compose_services':sum(len(x.get('services',[])) for x in inv['compose'])}
    (out/'SOURCE_INVENTORY.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n','utf-8')
    md=[f'# {a.label} 源码机器清单','',f'- 扫描根：`{root.name}/`（不记录绝对部署路径）',f'- 统计：`{json.dumps(inv["summary"],ensure_ascii=False)}`','', '## 完整受检源码文件树','```text',*fs,'```','','## FastAPI 路由']
    for x in inv['fastapi_routes']: md.append(f'- `{x["method"]} {x["path"]}` → `{x["file"]}::{x["function"]}()`；依赖：`{", ".join(x["dependencies"]) or "未在装饰器声明"}`')
    md += ['', '## Vue 组件']
    for x in inv['vue_components']: md.append(f'- `{x["file"]}` / `{x["name"]}`：props={x["props"] or []}；events={x["events"] or []}；state={x["state"] or []}；media={x["media_queries"] or []}')
    md += ['', '## Alembic 迁移']
    for x in inv['migrations']: md.append(f'- `{x["revision"]}` ← `{x["down_revision"]}`：`{x["file"]}`')
    md += ['', '## Compose']
    for c in inv['compose']:
        md.append(f'- `{c["file"]}`')
        for s in c.get('services',[]): md.append(f'  - `{s["name"]}`：ports={s["ports"]} volumes={s["volumes"]} networks={s["networks"]}')
    md += ['', '## 依赖版本（来自声明文件）','```json',json.dumps(inv['dependencies'],ensure_ascii=False,indent=2),'```','']
    (out/'SOURCE_INVENTORY.md').write_text('\n'.join(md),'utf-8')
    print(json.dumps(inv['summary'],ensure_ascii=False))
if __name__=='__main__':main()
