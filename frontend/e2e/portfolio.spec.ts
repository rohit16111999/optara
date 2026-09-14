import {test,expect} from '@playwright/test';

test('saved real run portfolio opens without inference',async({page})=>{
 const mutations:string[]=[];const errors:string[]=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',route=>{
  if(!['GET','HEAD','OPTIONS'].includes(route.request().method())){
   mutations.push(`${route.request().method()} ${route.request().url()}`);
   return route.abort();
  }
  return route.continue();
 });
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Execute',exact:true})).toBeVisible();
 const nav=page.getByRole('navigation',{name:'Main navigation'});
 await expect(nav.getByRole('button')).toHaveCount(3);
 await nav.getByRole('button',{name:/^Runs/}).click();
 await page.getByRole('button',{name:'Inspect run 9dbae5a2'}).click();
 await expect(page.getByRole('heading',{name:'Selected Execution',exact:true})).toBeVisible();
 await expect(page.locator('.selected-execution')).toContainText('openai/gpt-oss-20b');
 await expect(page.locator('.selected-execution')).toContainText('Focused');
 await expect(page.getByRole('heading',{name:'Why This Execution?',exact:true})).toBeVisible();
 await expect(page.locator('.chosen-recipe')).toContainText('Selected');
 await expect(page.locator('.scheduler-reason')).not.toBeEmpty();
 await expect(page.getByTestId('result-output')).toHaveText('703');
 await expect(page.locator('.evaluation-note')).toContainText('OBJECTIVE EVALUATION');
 const evidence=page.locator('details').filter({has:page.locator('summary').filter({hasText:/^Execution Evidence$/})});
 await expect(evidence).toBeVisible();
 await expect(evidence).toContainText('$0.00000584');
 await expect(evidence).toContainText('108 / 20 / 128');
 await expect(evidence).toContainText('exact_match');
 await expect(evidence).toContainText('HIT');
 await expect(evidence).toContainText('MISS');
 await expect(evidence.getByRole('link',{name:'VERIFY IN WEAVE ↗'})).toHaveAttribute('href','https://wandb.ai/models-student1155/optara/r/call/01a098ad-631e-76a8-af46-c4f5b4f347e3');
 await nav.getByRole('button',{name:'Evaluations',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Evaluations',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Quality / cost frontier',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Quality / latency frontier',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Recipe performance',exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'OPEN REPRODUCIBLE EVALUATION NOTEBOOK ↗'})).toHaveAttribute('href',/molab\.marimo\.io/);
 expect(mutations).toEqual([]);
 expect(errors).toEqual([]);
});
