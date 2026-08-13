#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
inv=json.loads(Path(sys.argv[1]).read_text())
doc=Path(sys.argv[2]).read_text()
public=(len(sys.argv)>3 and sys.argv[3]=='public')
missing={'routes':[],'components':[],'migrations':[],'files':[]}
for r in inv['fastapi_routes']:
    token_method=f'`{r["method"]}`'
    token_path=f'`{r["path"]}`'
    if token_method not in doc or token_path not in doc: missing['routes'].append(f'{r["method"]} {r["path"]}')
for c in inv['vue_components']:
    if c['file'] not in doc: missing['components'].append(c['file'])
for m in inv['migrations']:
    if m['revision'] not in doc: missing['migrations'].append(m['revision'])
for f in inv['files']:
    if f not in doc: missing['files'].append(f)
forbidden=[]
if public:
    patterns={
      'private_ip':r'(?<![\d.])(?:10\.\d{1,3}(?:\.\d{1,3}){2}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![\d.])',
      'real_domain':r'xxfly\.top',
      'enterprise_brands':r'浪潮|联想|华为|新华三|中兴|深信服|数聚红芯',
      'secret_shape':r'(?i)(?:sk-[A-Za-z0-9_-]{16,}|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|password\s*[:=]\s*[^$<{\s][^\s]{5,})',
    }
    for name,p in patterns.items():
      hits=sorted(set(re.findall(p,doc)))
      if hits: forbidden.append({'pattern':name,'hits':hits[:10]})
result={'summary':inv['summary'],'document_lines':doc.count('\n')+1,'coverage':{k:{'expected':len(inv['fastapi_routes'] if k=='routes' else inv['vue_components'] if k=='components' else inv['migrations'] if k=='migrations' else inv['files']),'missing':len(v),'missing_items':v[:20]} for k,v in missing.items()},'forbidden':forbidden}
print(json.dumps(result,ensure_ascii=False,indent=2))
if any(missing.values()) or forbidden: sys.exit(1)
