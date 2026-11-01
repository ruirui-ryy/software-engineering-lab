"""Package the course deliverable without including tools, caches, or source UI code."""
from pathlib import Path
import argparse
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
UML_NAMES = {
    '01-class': 'UML类图',
    '02-components': 'UML组件图',
    '03-event-state': 'UML活动状态图',
    '04-registration-state': 'UML报名状态图',
    '05-register-sequence': 'UML报名时序图',
    '06-cancel-promote-sequence': 'UML取消与递补时序图',
    '07-checkin-sequence': 'UML检票时序图',
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--student-id', required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not args.student_id.isdigit() or any(c in args.name for c in '/\\:'):
        raise ValueError('Invalid student ID or name')
    folder = f'实验2_{args.student_id}_{args.name}'
    archive = ROOT / f'{folder}.zip'
    report = ROOT / 'report/实验报告.pdf'
    reader = PdfReader(report)
    assert args.student_id in (reader.pages[0].extract_text() or '')
    assert all(p.mediabox.height > p.mediabox.width for p in reader.pages)
    entries = [(report, '实验报告.pdf')]
    for stem, name in UML_NAMES.items():
        for suffix in ['.png', '.puml']:
            entries.append((ROOT / f'uml/{stem}{suffix}', f'UML/{name}{suffix}'))
    images = sorted((ROOT / 'ui/exports').glob('*.png'))
    assert len(images) >= 18
    entries.extend((p, 'UI界面/' + p.name) for p in images)
    for source, rel in entries:
        assert source.is_file(), str(source)
        if source.suffix == '.png':
            with Image.open(source) as image:
                image.verify()
    with ZipFile(archive, 'w', ZIP_DEFLATED, compresslevel=6) as z:
        for name in [folder + '/', folder + '/UML/', folder + '/UI界面/']:
            z.writestr(name, b'')
        for source, rel in entries:
            z.write(source, folder + '/' + rel)
    with ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(entries) + 3
        assert all(n.startswith(folder + '/') for n in z.namelist())
        for source, rel in entries:
            assert hashlib.sha256(z.read(folder + '/' + rel)).digest() == hashlib.sha256(source.read_bytes()).digest()
    result = {'archive': archive.name, 'report_pages': len(reader.pages), 'uml_pairs': len(UML_NAMES), 'ui_png': len(images), 'file_count': len(entries), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'zip_integrity_and_content_hashes': 'passed'}
    (ROOT / 'checks/submission-checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))

if __name__ == '__main__':
    main()
