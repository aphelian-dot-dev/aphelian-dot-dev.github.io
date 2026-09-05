"""Actual boss victory unlocks EASY 3D Dawn; 2D victories and losses do not."""
import json,time,tempfile
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
options=Options();options.add_argument('-headless');options.set_preference('webgl.force-enabled',True)
with tempfile.TemporaryDirectory() as folder,webdriver.Firefox(options=options) as d:
    file=Path(folder)/'index.html';file.write_bytes((ROOT/'index.html').read_bytes());d.set_window_size(1440,1000)
    d.get(file.as_uri()+'?debug=1');WebDriverWait(d,10).until(lambda d:d.execute_script('return !!window.__ORRERY__'))
    for view,won in [('3D',True),('2D',True),('3D',False)]:
        d.find_element('id','view'+view).click();d.find_element('id','riteButton').click()
        # View buttons cannot relabel an in-progress rite.
        d.execute_script('document.getElementById(arguments[0]).click()','view2D' if view=='3D' else 'view3D')
        if won:d.execute_script('window.__ORRERY__.forceBoss();window.__ORRERY__.defeatBoss()')
        else:d.execute_script('window.__ORRERY__.finish(false)')
        WebDriverWait(d,6).until(lambda d:d.execute_script('return ["won","lost"].includes(window.__ORRERY__.snapshot().mode)'))
        result=d.execute_script('''const feats=window.__ORRERY__.snapshot().achievements;
          const feat=feats.find(a=>a.id==='dawn-3d');
          const item=[...document.querySelectorAll('.achievement-item')].find(e=>e.textContent.includes('DAWN IN THREE DIMENSIONS'));
          return {feat,count:feats.length,visibleCount:document.getElementById('achievementCount').textContent,item:item?{unlocked:item.classList.contains('is-unlocked'),label:item.getAttribute('aria-label')}:null,title:document.getElementById('mainTitle').textContent};''')
        assert result['feat'],('Missing runtime 3D Dawn',result)
        expected=view=='3D' and won
        assert result['feat']['unlocked']==expected and result['feat']['difficulty']=='EASY',result
        assert result['item']['unlocked']==expected and 'EASY' in result['item']['label'],result
        assert result['count']==8 and result['visibleCount'].endswith(' / 8'),result
        if won:assert result['title']=='DAWN',result
        if expected:d.save_screenshot(str(OUT/'dawn-3d-desktop.png'))
        print(view,won,json.dumps(result))
        d.find_element('id','homeButton').click()
print('PASS: genuine 3D boss victory, 2D exclusion, loss exclusion, result count, EASY label and run-view locking.')
