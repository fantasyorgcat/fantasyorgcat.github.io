"""Sequential before/after browser measurements against the same exported snapshot."""
import asyncio,json,functools,threading,http.server,math,sys,os,hashlib
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parent
BASE=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/fantasy-perf-8fd0754')
OUT=Path(sys.argv[2] if len(sys.argv)>2 else '/tmp/phase1-benchmark');OUT.mkdir(parents=True,exist_ok=True)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
from roto_data import read_report
assert json.loads((BASE/'data_snapshot.json').read_text(encoding='utf-8'))==json.loads((ROOT/'data_snapshot.json').read_text(encoding='utf-8')), 'Benchmark requires the identical source snapshot'
assert read_report(BASE/'index.html')==read_report(ROOT/'index.html'), 'Benchmark requires identical player/stat values'
servers=[]
for port,path in [(8791,str(BASE)),(8792,str(ROOT))]:
 server=http.server.ThreadingHTTPServer(('127.0.0.1',port),functools.partial(Quiet,directory=path));threading.Thread(target=server.serve_forever,daemon=True).start();servers.append(server)
async def settle(page):
 await page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
async def load(page,url):
 await page.goto(url,wait_until='load',timeout=180000)
 await page.wait_for_function("window.tables?.WCustom&&document.querySelectorAll('.table-toolbar').length>=1",timeout=180000)
 await settle(page);await page.wait_for_timeout(500)
 return await page.evaluate('''()=>{const t=window.__longTasks;return{fcp:performance.getEntriesByName('first-contentful-paint')[0]?.startTime,load:performance.getEntriesByType('navigation')[0].loadEventEnd,longTasks:t.reduce((s,e)=>s+e.duration,0),maxTask:Math.max(0,...t.map(e=>e.duration)),lastTaskEnd:Math.max(0,...t.map(e=>e.startTime+e.duration)),draws:window.__draws||{},elements:document.getElementsByTagName('*').length};}''')
async def interaction(page,kind,i):
 return await page.evaluate('''async ({kind,i})=>{const t=tables[activeWeek];let draws=0;const draw=()=>draws++;$(document).on('draw.dt.benchmark',draw);const insight=document.querySelector('#schedule-insights table'),start=performance.now();if(kind==='mode')switchDisplayMode(i%2?'AVG':'TOT',activeWeek);else if(kind==='period')switchStats(i%2?'LS':'L7',activeWeek);else if(kind==='page')t.page(i%2?'previous':'next').draw('page');else if(kind==='search')t.search(i%2?'':'Young').draw();else if(kind==='week')selectSeasonWeek(String(i%2));await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));$(document).off('draw.dt.benchmark',draw);return{ms:performance.now()-start,draws,insightsReplaced:insight!==document.querySelector('#schedule-insights table')};}''',{'kind':kind,'i':i})
async def main():
 fingerprints={name:hashlib.sha256(b''.join(p.name.encode()+p.read_bytes() for p in sorted(path.iterdir()) if p.name=='index.html' or p.suffix in ['.js','.css'])).hexdigest() for name,path in [('before',BASE),('after',ROOT)]}
 result={'base_sha':__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'method':'localhost same snapshot; cold=new context, warm=same-context navigation; 390px CPU4x is simulation; no production network measurements','runs':[]}
 if '--resume' in sys.argv and (OUT/'benchmark-results.json').exists():result=json.loads((OUT/'benchmark-results.json').read_text())
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
  for width,cpu in [(1440,1),(390,4)]:
   for version,port in ([('before',8791)] if '--baseline-only' in sys.argv else [('before',8791),('after',8792)]):
    if any(r['width']==width and r['version']==version and r.get('index_sha256')==fingerprints[version] for r in result['runs']):continue
    result['runs']=[r for r in result['runs'] if not (r['width']==width and r['version']==version)]
    entry={'index_sha256':fingerprints[version],'width':width,'cpu':cpu,'version':version,'cold':[],'warm':[],'interactions':{},'errors':[]}
    for n in range(5):
     c=await browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce');page=await c.new_page();page.on('pageerror',lambda e:entry['errors'].append(str(e)))
     await page.add_init_script("window.__longTasks=[];new PerformanceObserver(l=>{for(const e of l.getEntries())__longTasks.push({startTime:e.startTime,duration:e.duration})}).observe({type:'longtask',buffered:true});")
     cdp=await c.new_cdp_session(page);await cdp.send('Emulation.setCPUThrottlingRate',{'rate':cpu})
     for kind in ['cold','warm']:
      values=await load(page,f'http://127.0.0.1:{port}/');entry[kind].append(values);print(json.dumps({'version':version,'width':width,'run':n,'cache':kind,**values}),flush=True)
     if n==4:
      for kind in ['mode','period','page','search','week']:
       samples=[]
       # Include the first switch; don't prewarm either implementation.
       for i in range(30):samples.append(await interaction(page,kind,i))
       entry['interactions'][kind]=samples
       print(json.dumps({'version':version,'width':width,'operation':kind,'p95_ms':sorted(x['ms'] for x in samples)[math.ceil(.95*len(samples))-1],'draws_first':samples[0]['draws']}),flush=True)
     await c.close()
    result['runs'].append(entry);(OUT/'benchmark-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
  await browser.close()
 for s in servers:s.shutdown()
 print('BENCHMARK COMPLETE',flush=True)
asyncio.run(main())
