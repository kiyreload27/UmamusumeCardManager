import sys, traceback; sys.stdin = None; sys.stdout = None; sys.stderr = None; 
try: 
    from playwright.sync_api import sync_playwright
    p=sync_playwright().start()
    open('out.txt','w').write('SUCCESS')
    p.stop() 
except Exception as e: 
    open('out.txt','w').write(str(e)+'\n'+traceback.format_exc())
