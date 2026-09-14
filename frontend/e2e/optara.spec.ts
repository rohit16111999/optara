import {test,expect} from '@playwright/test';

test('execute renders without browser errors',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.getByRole('heading',{name:'Execute',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Run Optara'})).toBeEnabled();
 await expect(page.getByTestId('node-scheduler')).toBeVisible();
 await expect(page.getByText('Control plane online')).toBeVisible();
 expect(errors).toEqual([]);
});

test('form drives backend SSE, graph state and evaluated result',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Simulation',exact:true}).click();
 const answer=`BROWSER_${Date.now()}`;
 await page.getByLabel('Task prompt').fill(`Reply with exactly: ${answer}`);
 await page.getByLabel('Max budget').fill('0.01');await page.getByLabel('Deadline',{exact:true}).fill('30');
 await page.getByRole('button',{name:'Run Optara'}).click();
 await expect(page.getByTestId('result-output')).toHaveText(answer);
 await expect(page.getByTestId('node-profiler')).toHaveAttribute('data-status','complete');
 await expect(page.getByTestId('node-scheduler')).toHaveAttribute('data-status','complete');
 await expect(page.getByTestId('node-evaluator')).toHaveAttribute('data-status','complete');
 await expect(page.getByText('Scheduler reason',{exact:true})).toBeVisible();
 await expect(page.getByRole('log')).toContainText('Exact reference matched');
 await expect(page.getByText('Local fixtures · no model calls or sponsor traces')).toBeVisible();
});

test('failed exact constraint triggers bounded targeted repair',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Simulation',exact:true}).click();
 await page.getByRole('button',{name:'JSON + repair',exact:true}).click();
 await page.getByLabel('Reuse validated results').uncheck();
 // Different requested quality creates a distinct cache key without altering the fixture.
 await page.getByLabel('Quality target').fill('0.99');
 await page.getByRole('button',{name:'Run Optara'}).click();
 await expect(page.getByTestId('result-output')).toContainText('Ada');
 await expect(page.getByTestId('node-repair')).toHaveAttribute('data-status','complete');
 await expect(page.getByRole('log')).toContainText('Repair triggered');
});

test('API rejection appears as a clear error state',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Simulation',exact:true}).click();
 await page.route('**/api/runs',route=>route.request().method()==='POST'?route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:'Two jobs are already running. Wait for one to finish.'})}):route.continue());
 await page.getByRole('button',{name:'Run Optara'}).click();
 await expect(page.getByRole('status').filter({hasText:'Two jobs are already running'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Run Optara'})).toBeEnabled();
});

test('post-result shadow events update the graph and preserve the answer',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Simulation',exact:true}).click();
 const answer=`SHADOW_${Date.now()}`;
 await page.getByLabel('Task prompt').fill(`Reply with exactly: ${answer}`);
 await page.getByLabel('Reuse validated results').uncheck();
 await page.getByRole('button',{name:'Run Optara'}).click();
 await expect(page.getByTestId('result-output')).toHaveText(answer);
 await expect(page.getByRole('button',{name:'Run Optara'})).toBeEnabled();
 await page.locator('summary').filter({hasText:'Advanced Experiments'}).click();
 await page.getByRole('button',{name:'Test a shadow recipe'}).click();
 await expect(page.getByTestId('node-compare')).toHaveAttribute('data-status','complete');
 await expect(page.getByTestId('node-shadow')).toHaveAttribute('data-status','complete');
 await expect(page.getByTestId('result-output')).toHaveText(answer);
});

test('all product screens navigate and fit laptop widths',async({page})=>{
 await page.goto('/');
 for(const name of ['Runs','Evaluations','Execute']){
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:new RegExp(`^${name}`)}).click();
  await expect(page.getByRole('heading',{name,exact:true})).toBeVisible();
 }
 for(const width of [1440,1280,1024,390]){
  await page.setViewportSize({width,height:1000});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
  expect(overflow,`No document overflow at ${width}px`).toBeFalsy();
 }
});
