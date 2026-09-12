import argparse,pathlib,subprocess,json,re,hashlib
from project import ROOT
root=ROOT
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def scan(d, dump):
 meta=json.loads((d/'source.json').read_text(encoding='utf-8'));name=meta['device'];rom=meta['os'];result={'device':name,'os':rom,'stock_boot_sha256':sha(d/'boot.img'),'partitions':{},'modules':[]}
 for part in ['vendor','odm']:
  image=d/'partitions'/(part+'.img');pending=[('/',None)];dirs=0;files=0
  while pending:
   path,nid=pending.pop()
   text=subprocess.check_output([str(dump),'--ls','--path='+path,str(image)],text=True)
   dirs+=1
   for line in text.splitlines():
    m=re.fullmatch(r'\s*(\d+)\s+(\d+)\s+(.+)',line)
    if not m:continue
    ino,kind,base=m.groups()
    if base in ('.','..'):continue
    assert '/' not in base
    target=path.rstrip('/')+'/'+base
    if kind=='2':pending.append((target,ino))
    else:
     files+=1
     if re.search(r'\.ko(?:\.(?:gz|xz|zst))?$',base):
      out=d/'module-set'/part/target.lstrip('/');out.parent.mkdir(parents=True,exist_ok=True)
      if not out.exists():
       with out.open('xb') as f:subprocess.run([str(dump),'--cat','--nid='+ino,str(image)],stdout=f,check=True)
      assert out.read_bytes()[:4]==b'\x7fELF',target
      result['modules'].append({'partition':part,'path':target,'sha256':sha(out)})
  result['partitions'][part]={'sha256':sha(image),'size':image.stat().st_size,'directories_scanned':dirs,'files_scanned':files}
 (d/'module-inventory.json').write_text(json.dumps(result,indent=2))
 print(name,rom,len(result['modules']),'modules',flush=True)
if __name__ == "__main__":
 parser=argparse.ArgumentParser()
 parser.add_argument("--stock-dir",required=True,type=pathlib.Path)
 parser.add_argument("--dump-erofs",required=True,type=pathlib.Path)
 args=parser.parse_args()
 scan(args.stock_dir.resolve(),args.dump_erofs.resolve())
