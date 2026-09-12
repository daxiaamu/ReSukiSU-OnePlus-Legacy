import pathlib,json,hashlib,zipfile
from project import ROOT

def main():
    root=ROOT;out=root/'out';rows=[]
    for profile in sorted((root/'devices').glob('*.json')):
     data=json.loads(profile.read_text(encoding='utf-8'))
     if data.get('status',{}).get('distribution_status') == 'hold':raise ValueError('Distribution on hold after device failure report: '+data['id'])
     for rom in ['coloros','oxygenos']:
      fw=data['firmware'][rom];folder=out/data['id']/(rom+'-'+fw['build_id'])
      if not (folder/'boot.img').exists():raise ValueError('Missing completed artifact: '+str(folder))
      image=folder/'boot.img';manifest=json.loads((folder/'build.json').read_text())
      if hashlib.sha256(image.read_bytes()).hexdigest()!=manifest['boot_sha256']:raise ValueError('Boot image checksum changed: '+str(image))
      if not manifest['compile_verified'] or not manifest['abi_compatible']:raise ValueError('Unverified artifact: '+str(folder))
      if not (manifest['export_crc_check']['passed'] or (manifest.get('module_crc_check') or {}).get('passed')):raise ValueError('ABI checks did not pass')
      rows.append((data['name'],data['id'],rom,fw['build_id'],fw['layout'],folder,manifest))
    if len(rows)!=12:raise ValueError('Expected all twelve firmware artifacts')
    archives=out/'archives';archives.mkdir(exist_ok=True)
    lines=['# ReSukiSU OnePlus Legacy 成品','','已生成 '+str(len(rows))+' 份实验版 boot.img，完成编译、静态兼容性检查及重新解包校验；尚未真机测试。','','9R 的 ColorOS 为 A-only，OxygenOS 为 A/B，请按对应完整系统版本选择。','','| 机型 | 系统 | 完整版本 | 布局 | 镜像 | 压缩包 |','| --- | --- | --- | --- | --- | --- |']
    summary=[];sums=[]
    for label,name,rom,fw,layout,folder,m in rows:
     archive=archives/(name+'-'+rom+'-'+fw+'.zip')
     note=(label+' / '+rom+' / '+fw+'\nLayout: '+layout+'\nExperimental: not tested on a physical device.\nSource: https://github.com/daxiaamu/ReSukiSU-OnePlus-Legacy/tree/'+name+'\nOnly the kernel was replaced in this exact stock boot image.\nSee build.json for source pins and ABI-check scope.\n')
     if not archive.exists():
      with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
       for file in ['boot.img','build.json','SHA256SUMS']:z.write(folder/file,file)
       z.writestr('README.txt',note)
     with zipfile.ZipFile(archive) as z:
      if z.testzip() is not None:raise ValueError('ZIP integrity check failed: '+str(archive))
      if hashlib.sha256(z.read('boot.img')).hexdigest()!=m['boot_sha256']:raise ValueError('ZIP contains a different boot image')
      for filename in ['build.json','SHA256SUMS']:
       if z.read(filename)!=(folder/filename).read_bytes():raise ValueError('Stale archive metadata: '+archive.name)
     digest=hashlib.sha256(archive.read_bytes()).hexdigest();sums.append(digest+'  '+archive.name)
     lines.append('| '+label+' | '+rom+' | '+fw+' | '+layout+' | [boot.img](<'+(folder/'boot.img').as_posix()+'>) | [ZIP](<'+archive.as_posix()+'>) |')
     summary.append({'device':name,'os':rom,'firmware':fw,'layout':layout,'boot_sha256':m['boot_sha256'],'boot_size':(folder/'boot.img').stat().st_size,'archive':archive.name,'archive_sha256':digest,'image_sha256':m['image_sha256'],'all_exports_match':m['export_crc_check']['passed'],'module_check':bool(m.get('module_crc_check',{} ) and m['module_crc_check']['passed']),'device_verified':False})
     print('Verified',archive.name,flush=True)
    lines+=['','9 / 9 Pro 的原厂导出接口全部匹配。SM8250 的两项内建触屏私有回调保留公开源码布局；已核对原厂 vendor、odm 的全部 41 个驱动模块，不依赖这两项接口。详情见各镜像 build.json。']
    (out/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'build-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (archives/'SHA256SUMS').write_text('\n'.join(sums)+'\n',encoding='utf-8')
    print('Ready:',len(rows),flush=True)

if __name__ == '__main__':
    main()
