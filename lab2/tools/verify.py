"""Validate editable design artifacts and create review indexes; no report authoring."""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
MAP = {
 1: ('M01', '01-class,02-components,07-checkin-sequence', 'U01,U02,U11,U13,U16', '授权及越权路径；前端演示不能证明服务端防护'),
 2: ('M02', '01-class,02-components', 'U08,U09', '草稿、场次、票种及所属活动'),
 3: ('M02', '03-event-state', 'U10,U15', '提交、通过、驳回、修改重提'),
 4: ('M02', '03-event-state,01-class', 'U09,U10', '容量下限；复审字段与报名策略待确认'),
 5: ('M02', '03-event-state', 'U08,U10,U15', '六状态；未确认边不得新增'),
 6: ('M02', '03-event-state,07-checkin-sequence,05-register-sequence', 'U04,U05,U14,U15', '取消后禁止报名候补签到及并发写入'),
 7: ('M03', '02-components', 'U03,U04', '组合查询、空结果和失败'),
 8: ('M04', '01-class,04-registration-state,05-register-sequence', 'U04,U05,U07', '有效报名、关联票种场次与凭证'),
 9: ('M04', '04-registration-state,06-cancel-promote-sequence', 'U06,U07', '本人取消、释放占用、已签到不可取消'),
 10: ('M04', '04-registration-state,06-cancel-promote-sequence', 'U05,U06', '满额候补、有序递补，不占额'),
 11: ('M04', '04-registration-state', 'U06,U07', '七状态、合法边及禁止边'),
 12: ('M04', '05-register-sequence', 'U05', '最后名额竞争；需后端并发验收'),
 13: ('M04', '01-class,05-register-sequence', 'U05,U06', '有效报名唯一、同请求返回首次结果'),
 14: ('M04', '05-register-sequence,06-cancel-promote-sequence', 'U04,U05', '服务器时间、旧页面截止后提交'),
 15: ('M04', '04-registration-state,06-cancel-promote-sequence', 'U06,U07', '截止后候补失效、取消不递补'),
 16: ('M05', '01-class,07-checkin-sequence', 'U13,U14', '授权场次凭证核验及日志'),
 17: ('M05', '04-registration-state,07-checkin-sequence', 'U14,U12,U07', '重复核验不计数、场次结束未签到记缺席'),
 18: ('M02', '03-event-state,04-registration-state,07-checkin-sequence', 'U07,U15', '未签到已报名转活动取消，已签到历史保留'),
 19: ('跨模块', '01-class,02-components', 'U09,U07,U10,U14,U17,U18', '关系型保存建议、关联与无效引用检查'),
 20: ('M01', '01-class', 'U02', '保存重复账号标识时拒绝'),
 21: ('M04', '01-class,04-registration-state,06-cancel-promote-sequence', 'U04,U09,U12', '已报名+已签到占额、候补不占、剩余非负'),
 22: ('M06', '02-components,04-registration-state', 'U12', '容量人数口径、结束后签到率及零分母'),
 23: ('M06', '02-components', 'U11', '场次票种状态筛选、完整CSV、失败无残缺成功文件'),
 24: ('M06', '02-components', 'U16', '管理员平台汇总；具体指标待确认'),
 25: ('M08', '01-class,02-components,07-checkin-sequence', 'U17', '操作人、时间、对象、结果及失败日志'),
 26: ('M07', '01-class,02-components,05-register-sequence', 'U18', '失败补发，不回滚已成功报名；操作角色待确认'),
 28: ('跨模块', '02-components,05-register-sequence,06-cancel-promote-sequence,07-checkin-sequence', 'U05,U09,U14', '事务边界与统一锁序；故障注入须后续实现'),
 29: ('M03', '02-components', 'U03', '1万活动/20并发/100次中至少95次成功且≤1秒；环境待确认'),
 30: ('M01', '02-components,07-checkin-sequence', 'U11,U13,U14,U17', '服务端越权拒绝且数据不变，当前仅设计示例')
}
UI_NOTES = {
 'U01': ('示例账号登录并进入对应角色工作台。', '账号、密码、示例身份；真实身份来自服务端。', '登录失败；不提供开放注册或任意权限授予。'),
 'U02': ('维护自己的账号标识。', '当前角色、账号标识、唯一性反馈。', '重复标识拒绝保存；创建账号和角色管理主体待确认。'),
 'U03': ('按关键词、城市、类别、日期组合查询。', '筛选区、活动卡片、匹配数和详情入口。', '空结果、加载、请求失败；排序规则待确认。'),
 'U04': ('查看活动并选择场次与票种。', '活动介绍、组织者、地点、开放截止、容量状态。', '满额可候补；未开放、截止、取消时禁止新增。'),
 'U05': ('确认报名或主动选择候补。', '活动、场次、票种、本人、结果反馈。', '最后名额竞争、重复有效报名、截止、取消、未知结果重试；不含支付。'),
 'U06': ('查看本人报名、候补和历史记录。', '活动、场次、状态及详情入口。', '空记录、截止后候补失效；不显示他人名单。'),
 'U07': ('查看本人的当前报名凭证与取消入口。', '凭证编号、状态、场次、票种、参与者。', '已签到不可取消；候补、失效、缺席、取消均不可用于签到。'),
 'U08': ('管理所属活动并进入编辑或审核进度。', '活动列表、场次票种数、状态、更新日期。', '空列表；不显示他人活动管理入口。'),
 'U09': ('维护活动、场次、票种并保存或提交审核。', '字段编辑、票种添加、容量、保存状态。', '容量低于占用数拒绝；复审字段与双层容量待确认。'),
 'U10': ('查看提交、驳回、发布和重新提交进度。', '审核状态、意见、时间线。', '驳回后修改重提；复审期间报名规则待确认。'),
 'U11': ('筛选所属活动名单并导出CSV。', '场次、票种、状态、分页、导出结果。', '空名单、无权、导出中断；失败时不下载残缺文件。'),
 'U12': ('查看活动名额、记录状态和结束后签到率。', '容量、占用、剩余、候补；结束后签到和缺席人数。', '零分母显示暂无数据；未结束只展示人数是待确认期间的设计建议。'),
 'U13': ('选择已授权场次进入核验。', '活动、场次、时间、地点和已签到人数。', '无授权场次；授权主体与检票窗口待确认。'),
 'U14': ('核验凭证并反馈签到结果。', '编号输入、核验结果、当前签到人数。', '重复不计数、无效凭证、无权、活动取消、候补不得签到。'),
 'U15': ('管理员审核活动及取消满足条件的违规活动。', '活动资料、审核意见、通过、驳回、取消确认。', '状态冲突拒绝旧请求；取消影响提示；完整取消起点集合待确认。'),
 'U16': ('管理员查看平台级汇总。', '活动和报名汇总区域占位。', '指标未确定，禁止编造已确认指标；空数据。'),
 'U17': ('管理员查询关键操作及成功失败结果。', '条件区、日志列表、详情弹窗。', '空结果、越权；筛选字段为设计建议，保存期限待确认。'),
 'U18': ('独立预览通知失败与补发处理。', '通知、业务关联、接收人、发送状态和补发操作。', '补发中、失败、成功；不改变报名。操作角色、渠道、触发时机和次数待确认。')
}

def main():
    pages = json.loads((ROOT/'planning/pages.json').read_text(encoding='utf-8'))
    result = {'scope': '设计覆盖和本地界面验证；非后端验收', 'checks': []}
    def check(name, ok, detail=''):
        result['checks'].append({'name': name, 'passed': bool(ok), 'detail': detail})
    baseline = json.loads((ROOT/'checks/baseline.json').read_text(encoding='utf-8'))
    for file, digest in baseline['files'].items():
        check('保留实验一文件 '+file, hashlib.sha256((REPO/file).read_bytes()).hexdigest().upper()==digest)
    for tag, commit in baseline['tags'].items():
        actual=subprocess.check_output(['git','rev-parse',tag+'^{commit}'],cwd=REPO,text=True).strip()
        check('保留标签 '+tag, actual==commit)
    requirement_text=(REPO/'requirements.md').read_text(encoding='utf-8')
    import re
    titles={int(n):title for n,title in re.findall(r'^## REQ-(\d+) (.+)$',requirement_text,re.M)}
    with (ROOT/'planning/traceability.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['需求ID','需求名称','状态','模块','UML源文件','UI页面','检查场景','验证层级'])
        for n,(module,figs,uis,scenario) in MAP.items():
            w.writerow([f'REQ-{n:03}',titles[n],'已确认目标；条内缺口仍待确认',module,figs,uis,scenario,'设计覆盖；UI行为为内存示例'])
        w.writerow(['REQ-027',titles[27],'已变更→REQ-023，不计数','M06','02-components','U11','复用REQ-023导出失败检查','历史追踪'])
    check('29条有效需求完整覆盖',set(MAP)==set(range(1,31))-{27})
    check('18个基础页面',len(pages)==18)
    page_ids={p['id'] for p in pages}
    for n,(_,figs,uis,_) in MAP.items():
        check(f'REQ-{n:03}追踪目标存在',all((ROOT/f'uml/{fig}.puml').exists() for fig in figs.split(',')) and set(uis.split(','))<=page_ids)
    puml=list((ROOT/'uml').glob('*.puml'))
    check('7张UML源图',len(puml)==7)
    for src in puml:
        check(src.stem+'PNG及SVG存在',src.with_suffix('.png').exists() and src.with_suffix('.svg').exists())
        svg=src.with_suffix('.svg').read_text(encoding='utf-8')
        check(src.stem+'无错误图',not any(s in svg for s in ['Syntax Error','An error has occurred','Error line']))
    check('至少四种图',all(any(s in p.read_text(encoding='utf-8') for p in puml) for s in ['类图｜','组件图｜','状态图｜','时序图｜']))
    ui=json.loads((ROOT/'checks/ui-results.json').read_text(encoding='utf-8'))
    check('UI交互检查全部通过','failure' not in ui and all(x['passed'] for x in ui['assertions']))
    check('导出数量匹配清单',len(ui['exported'])==sum(len(p['states']) for p in pages))
    check('各场景图片可读取',all(Image.open(ROOT/'ui/exports'/item['file']).width>=1000 for item in ui['exported']))
    notes=['# UI设计说明（技术工作记录）','', '所有页面均为可编辑本地原型，截图与URL参数对应；非正式软件安全或性能验收。顶部预览栏属于原型工具。通知页权限归属仍待确认。','']
    for p in pages:
        goal,contents,exceptions=UI_NOTES[p['id']]
        notes += [f"## {p['id']} {p['title']}",'',f"- 角色：{p['role']}；模块：{p['module']}；需求：{', '.join(p['reqs'])}。",f'- 目的与操作：{goal}',f'- 主要内容：{contents}',f'- 异常与边界：{exceptions}',f"- 场景：{', '.join(p['states'])}。",f"- 源文件入口：`source/index.html?page={p['id']}`。",'']
    (ROOT/'ui/page-notes.md').write_text('\n'.join(notes),encoding='utf-8')
    font_path=Path('C:/Windows/Fonts/msyh.ttc')
    font=ImageFont.truetype(str(font_path),18)
    for kind,files,cols,thumbw,thumbh in [
        ('ui-contact-sheet',[(ROOT/'ui/exports'/x['file'],f"{x['id']} {next(p['title'] for p in pages if p['id']==x['id'])}") for x in ui['exported'] if x['state']=='default'],3,420,310),
        ('uml-contact-sheet',[(p.with_suffix('.png'),p.stem) for p in puml],2,620,510)]:
        rows=(len(files)+cols-1)//cols
        canvas=Image.new('RGB',(cols*(thumbw+20)+20,rows*(thumbh+45)+20),'#e9eee7');draw=ImageDraw.Draw(canvas)
        for i,(file,label) in enumerate(files):
            im=Image.open(file).convert('RGB');im.thumbnail((thumbw,thumbh))
            x=20+(i%cols)*(thumbw+20);y=20+(i//cols)*(thumbh+45)
            canvas.paste(im,(x,y));draw.text((x,y+thumbh+6),label,font=font,fill='#244c3c')
        canvas.save(ROOT/f'checks/{kind}.jpg',quality=90)
    html=['<!doctype html><meta charset="utf-8"><title>实验二设计图片索引</title><style>body{font:15px Microsoft YaHei;background:#f4f6ef;color:#214e3d;margin:40px}h2{margin-top:40px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}a{color:inherit}img{width:100%;background:white;border:1px solid #ced9cf}figure{margin:0}figcaption{padding:9px}</style><h1>实验二 · 设计图片索引</h1><p>可点击图片打开原图。全部使用虚构数据；报告已完成，完整设计源文件保留在工作区。</p><a href="../ui/source/index.html">进入交互原型 →</a><h2>UML</h2><div class="grid">']
    for p in puml:
        href='../uml/'+p.with_suffix('.png').name
        html.append(f'<figure><a href="{href}"><img src="{href}"></a><figcaption>{p.stem}</figcaption></figure>')
    html.append('</div><h2>UI基础页面</h2><div class="grid">')
    for item in ui['exported']:
        if item['state']!='default':continue
        href='../ui/exports/'+item['file']
        html.append(f'<figure><a href="{href}"><img src="{href}"></a><figcaption>{item["file"]}</figcaption></figure>')
    html.append('</div><h2>异常及边界状态</h2><ul>')
    for item in ui['exported']:
        if item['state']=='default':continue
        html.append(f'<li><a href="../ui/exports/{item["file"]}">{item["file"]}</a></li>')
    html.append('</ul>')
    (ROOT/'checks/gallery.html').write_text('\n'.join(html),encoding='utf-8')
    result['passed']=sum(x['passed'] for x in result['checks']);result['total']=len(result['checks'])
    (ROOT/'checks/artifact-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'total':result['total'],'failed':[x for x in result['checks'] if not x['passed']]},ensure_ascii=False,indent=2))
    return int(result['passed']!=result['total'])

if __name__=='__main__':raise SystemExit(main())
