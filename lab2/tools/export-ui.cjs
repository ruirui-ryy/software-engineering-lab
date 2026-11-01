/* Run with node. Uses installed Playwright; exports PNG and tests actual browser interactions. */
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'C:/Users/26545/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = path.resolve(__dirname, '..');
let base;
const output = path.join(root, 'ui/exports');
const checks = path.join(root, 'checks');
const results = { scope: '本地UI原型；不覆盖服务端安全、事务或正式性能验收', exported: [], assertions: [], consoleErrors: [], layoutIssues: [] };
function assert(value, name, details='') { results.assertions.push({name, passed:!!value, details}); if (!value) throw new Error(name+': '+details); }
(async()=>{
 const server=await require('./preview.cjs').start(0);
 base=`http://127.0.0.1:${server.address().port}/`;
 const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--disable-gpu']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 const page=await context.newPage();
 page.on('pageerror',e=>results.consoleErrors.push(String(e)));
 async function open(id,state='default'){await page.goto(`${base}?page=${id}&state=${state}`);await page.evaluate(()=>document.fonts.ready);}
 try {
  await open('U01');
  const pages=await page.evaluate(()=>window.PROTOTYPE.pages);
  fs.writeFileSync(path.join(root,'planning/pages.json'),JSON.stringify(pages,null,2));
  for(const p of pages){
   for(const state of p.states){
    await open(p.id,state);
    const layout=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth,body:document.body.scrollHeight,missing:[...document.querySelectorAll('button,a,input,select,textarea')].filter(e=>!e.getAttribute('aria-label')&&!e.textContent.trim()&&!e.closest('label')&&!e.getAttribute('placeholder')).map(e=>e.outerHTML)}));
    if(layout.scroll>layout.width)results.layoutIssues.push({page:p.id,state,overflow:layout.scroll-layout.width});
    const name=`${p.id}_${p.title}${state==='default'?'':'_'+state}.png`;
    await page.screenshot({path:path.join(output,name),fullPage:true,animations:'disabled'});
    results.exported.push({id:p.id,state,file:name,width:layout.width,height:Math.max(1000,layout.body)});
   }
  }
  await open('U03');
  await page.locator('#keyword').fill('自然');
  await page.locator('#city').selectOption({label:'杭州'});
  await page.getByRole('button',{name:'查询活动',exact:true}).click();
  assert(await page.locator('.event-body h3').count()===1,'组合查询仅返回匹配活动');
  assert((await page.locator('.event-body h3').innerText()).includes('自然'),'查询结果为自然工作坊');
  await page.getByRole('link',{name:'查看详情',exact:false}).click();
  assert((await page.locator('.hero-title').innerText()).includes('自然观察'),'活动详情保留选中的活动身份');
  await page.getByRole('link',{name:'登记候补',exact:false}).click();
  assert((await page.locator('main').innerText()).includes('秋日自然观察工作坊'),'报名确认与上一步活动一致');
  await open('U04');await page.locator('#ticket-choice').selectOption({label:'交流席'});
  await page.getByRole('link',{name:'确认报名',exact:false}).click();
  assert((await page.locator('.data-pairs').innerText()).includes('交流席'),'所选票种传递到报名确认');
  await open('U03');
  await page.locator('#keyword').fill('不存在的活动');
  await page.getByRole('button',{name:'查询活动',exact:true}).click();
  assert((await page.locator('main').innerText()).includes('还没有匹配的活动'),'空结果状态');
  await open('U05','unknown');
  await page.getByRole('button',{name:'查询并重试原请求'}).click();
  assert((await page.locator('main').innerText()).includes('报名成功'),'原请求重试展示首次成功结果');
  await open('U05','full');
  await page.getByRole('button',{name:'确认登记候补'}).click();
  assert((await page.locator('main').innerText()).includes('已加入候补'),'满额候补确认');
  await open('U07');
  assert(await page.evaluate(()=>window.PROTOTYPE.roster.find(r=>r.code==='JH-0001').ticket==='标准席') && (await page.locator('.ticket-main').innerText()).includes('标准席'),'同一示例报名在名单与凭证中票种一致');
  await page.getByRole('button',{name:'取消报名',exact:true}).click();
  assert(await page.locator('dialog').isVisible(),'取消报名先展示确认');
  await page.screenshot({path:path.join(output,'U07_cancel-confirm.png'),fullPage:true});
  await page.getByRole('button',{name:'确认取消',exact:true}).click();
  assert((await page.locator('main').innerText()).includes('当前状态：已取消'),'确认后凭证状态更新');
  assert(await page.locator('.credential').count()===0,'已取消记录不展示有效入场凭证');
  await open('U07','checked');
  assert(await page.getByRole('button',{name:'已签到，不可取消报名'}).isDisabled(),'已签到禁止取消');
  await open('U14');
  await page.getByRole('button',{name:'核验并签到'}).click();
  assert((await page.locator('#check-result').innerText()).includes('签到成功'),'首次核验成功');
  assert((await page.locator('#check-count').innerText()).includes('25'),'首次签到增加一次计数');
  await page.getByRole('button',{name:'核验并签到'}).click();
  assert((await page.locator('#check-result').innerText()).includes('已签到'),'重复核验反馈');
  assert((await page.locator('#check-count').innerText()).includes('25'),'重复签到不增加计数');
  await page.locator('#credential-code').fill('INVALID');
  await page.getByRole('button',{name:'核验并签到'}).click();
  assert((await page.locator('#check-result').innerText()).includes('凭证无效'),'无效凭证被拒绝');
  for(const state of ['forbidden','cancelled','waiting']){
   await open('U14',state);await page.getByRole('button',{name:'核验并签到'}).click();
   assert(!(await page.locator('#check-result').innerText()).includes('签到成功'),`${state}场景拒绝签到`);
   assert((await page.locator('#check-count').innerText()).includes('24'),`${state}场景不增加计数`);
  }
  await open('U09','capacity');
  await page.getByRole('button',{name:'提交审核',exact:false}).click();
  assert((await page.locator('#capacity-error').innerText()).includes('不能低于'),'容量下限校验');
  await page.locator('#capacity').fill('130');
  await page.getByRole('button',{name:'保存草稿'}).click();
  assert((await page.locator('#save-status').innerText()).includes('草稿已保存'),'草稿保存反馈');
  await page.getByRole('button',{name:'添加票种',exact:false}).click();
  assert(await page.locator('#extra-tickets input').count()===2,'可新增票种字段');
  await page.getByRole('button',{name:'添加场次',exact:false}).click();
  assert(await page.locator('.extra-session').count()===1,'可新增场次及票种字段');
  await page.locator('[data-session-end]').fill('2026-11-14T18:00');
  await page.getByRole('button',{name:'保存草稿'}).click();
  assert((await page.locator('#capacity-error').innerText()).includes('新增场次结束'),'新增场次时间校验');
  await page.getByRole('button',{name:'移除此新增场次'}).click();
  assert(await page.locator('.extra-session').count()===0,'可移除未保存的新增场次');
  await open('U08');await page.getByRole('link',{name:'创建活动',exact:false}).click();
  assert(await page.locator('#event-name').inputValue()==='','创建入口打开空白活动名称');
  await page.locator('#event-name').fill('测试新活动');await page.locator('#event-place').fill('测试场地');await page.locator('#event-description').fill('测试说明');
  await page.locator('#capacity').fill('10');await page.getByRole('button',{name:'保存草稿'}).click();
  assert((await page.locator('#save-status').innerText()).includes('草稿已保存'),'新建活动按0占用校验而非套用已有活动');
  await open('U08');await page.getByRole('link',{name:'账号设置',exact:false}).click();
  assert((await page.locator('.profile').innerText()).includes('组织者'),'账号页保留来源身份');
  await open('U11');
  await page.locator('#roster-status').selectOption({label:'候补中'});
  await page.getByRole('button',{name:'筛选名单'}).click();
  assert(await page.locator('tbody tr').count()===6,'候补名单筛选6条');
  const waitDownload=page.waitForEvent('download');
  await page.getByRole('button',{name:'导出 CSV'}).click();
  const download=await waitDownload;
  const downloaded=path.join(checks,'sample-export.csv');await download.saveAs(downloaded);
  const csv=fs.readFileSync(downloaded,'utf8');
  assert(csv.split('\r\n').length===7,'导出CSV与筛选后的6条记录一致');
  assert(!csv.includes('已签到'),'候补筛选CSV不包含已签到');
  await open('U11','export-error');
  let downloadCount=0;const handler=()=>downloadCount++;page.on('download',handler);
  await page.getByRole('button',{name:'导出 CSV'}).click();await page.waitForTimeout(150);
  assert(downloadCount===0,'导出故障不下载残缺成功文件');page.off('download',handler);
  await open('U11','forbidden');
  assert(await page.locator('tbody').count()===0,'无权场景隐藏受保护名单');
  assert(await page.getByRole('button',{name:'导出 CSV'}).isDisabled(),'无权场景禁止导出按钮');
  await open('U15');await page.getByRole('button',{name:'驳回修改'}).click();
  assert((await page.locator('#review-error').innerText()).includes('填写驳回原因'),'驳回需填写原因（设计建议）');
  await page.locator('#review-reason').fill('请补充场地信息');await page.getByRole('button',{name:'驳回修改'}).click();
  assert((await page.locator('#review-result').innerText()).includes('已驳回'),'审核驳回交互');
  await open('U15','conflict');await page.getByRole('button',{name:'通过并发布'}).click();
  assert((await page.locator('#review-result').innerText()).includes('状态已变化'),'审核冲突拒绝旧请求');
  await open('U15');await page.getByRole('button',{name:'取消违规活动'}).click();
  await page.screenshot({path:path.join(output,'U15_cancel-confirm.png'),fullPage:true});
  await page.getByRole('button',{name:'确认取消活动',exact:true}).click();
  assert(await page.getByRole('button',{name:'通过并发布'}).isDisabled(),'活动取消后禁止旧审核按钮');
  await open('U17');await page.locator('#log-status').selectOption({label:'失败'});await page.getByRole('button',{name:'查询日志'}).click();
  assert(await page.locator('tbody tr').count()===2,'失败日志查询');
  await page.getByRole('button',{name:'查看',exact:true}).first().click();
  assert((await page.locator('dialog').innerText()).includes('失败：写入中断'),'日志详情包含失败结果');
  await page.screenshot({path:path.join(output,'U17_log-detail.png'),fullPage:true});
  await open('U18');await page.getByRole('button',{name:'补发通知'}).click();await page.waitForTimeout(700);
  assert((await page.locator('#notification-status').innerText()).includes('已发送'),'通知补发成功');
  assert((await page.locator('#notice-result').innerText()).includes('关联报名仍有效'),'通知处理保留报名结果');
  await open('U18','failed');await page.getByRole('button',{name:'补发通知'}).click();await page.waitForTimeout(700);
  assert((await page.locator('#notification-status').innerText()).includes('发送失败'),'通知补发失败保留结果');
  await open('U02');await page.locator('#account-name').fill('admin.demo');await page.getByRole('button',{name:'保存修改'}).click();
  assert((await page.locator('#account-error').innerText()).includes('已存在'),'账号标识唯一校验演示');
  await open('U12','zero');assert((await page.locator('main').innerText()).includes('暂无数据'),'统计零分母反馈');
  await page.setViewportSize({width:390,height:844});
  for(const id of ['U01','U03','U07','U14']){
   await open(id);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
   assert(!overflow,`${id}窄屏无页面水平溢出`);
   await page.screenshot({path:path.join(output,`${id}_mobile.png`),fullPage:true});
  }
  assert(results.consoleErrors.length===0,'所有页面无JavaScript运行错误',results.consoleErrors.join('\n'));
  assert(results.layoutIssues.length===0,'所有导出场景无页面水平溢出',JSON.stringify(results.layoutIssues));
 } catch(e){ results.failure=String(e.stack||e);process.exitCode=1; }
 finally {
  fs.writeFileSync(path.join(checks,'ui-results.json'),JSON.stringify(results,null,2));
  await browser.close();
  server.close();
  console.log(JSON.stringify({exported:results.exported.length,assertions:results.assertions.length,passed:results.assertions.filter(x=>x.passed).length,layoutIssues:results.layoutIssues,failure:results.failure},null,2));
 }
})();
