# Ver. 0.1.1-beta

import sys
import os
import re
import time
import math
import argparse
import xml.etree.ElementTree as ET
import xml.dom.minidom as md
from PIL import Image
from tqdm import tqdm

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('dir', help='target dir/parent dir of target dir')
parser.add_argument('-p', '--prompt', action='store_true', help='parse prompts')
parser.add_argument('-t', '--tag', action='store_true', help='parse tags')
parser.add_argument('-c', '--categoly', nargs='*', help='specified category name')
parser.add_argument('-s', '--sub', action='store_true', help='search files in sub dirs of specified dir')
parser.add_argument('-sr', '--sub-recursive', type=int, help='search files in sub dirs of specified dir recursively')
parser.add_argument('-o', '--output', help='output xml file name')
parser.add_argument('-pf', '--prefix', help='prefix of dir name include (-s option required)')
parser.add_argument('-sf', '--suffix', help='suffix of dir name include (-s option required)')
parser.add_argument('-expf', '--exclude-prefix', help='prefix of dir name exclude (-s option required)')
parser.add_argument('-exsf', '--exclude-suffix', help='suffix of dir name exclude (-s option required)')
parser.add_argument('-da', '--days-after', type=float, help='specify the number of days before now, and PNG files modified after then are included (-s option required)')
parser.add_argument('-db', '--days-before', type=float, help='specify the number of days before now, and PNG files modified before then are included (-s option required)')
parser.add_argument('-tda', '--tag-days-after', type=float, help='specify the number of days before now, and PNG files related tag file modified after then are included (-s option required)')
parser.add_argument('-tdb', '--tag-days-before', type=float, help='specify the number of days before now, and PNG files related tag file modified before then are included (-s option required)')
parser.add_argument('-n', '--no-generation', action='store_true', help='do not generate XML file')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose mode')
args = parser.parse_args()

if not os.path.isdir(args.dir):
    print('Specified path is not dir')
    sys.exit()

if not (args.prompt or args.tag or args.categoly):
    print('Specify at least one of -p, -t or -c')
    sys.exit()

def recursive(path, depth):
    for child in os.listdir(path):
        child_path = os.path.join(path, child)
        if os.path.isdir(child_path):
            dirs.append(child_path)
            if depth > 1:
                recursive(child_path, depth - 1)

dirs = []

if args.sub or args.sub_recursive:
    recursive(os.path.abspath(args.dir), args.sub_recursive if args.sub_recursive is not None else 1)
else:
    dirs.append(os.path.abspath(args.dir))

now = time.time()
dirs = list(filter(lambda e: (args.prefix is None or e.startswith(args.prefix))
            and (args.suffix is None or e.endswith(args.suffix))
            and (args.exclude_prefix is None or not e.startswith(args.exclude_prefix))
            and (args.exclude_suffix is None or not e.endswith(args.exclude_suffix)), dirs))

files = []
for dirname in dirs:
    print('Searching dir: ' + dirname)
    for file in os.listdir(dirname):
        pngfile_path = os.path.join(dirname, file)
        txtfile_path = re.sub(r'\.png$', '.txt', pngfile_path)
        pngmtime = os.path.getmtime(pngfile_path)
        txtmtime = os.path.getmtime(txtfile_path) if os.path.isfile(txtfile_path) else 0
        if (os.path.isfile(pngfile_path)
                    and file.endswith('.png')
                    and (args.days_after is None or pngmtime > now - args.days_after * 86400)
                    and (args.days_before is None or pngmtime < now - args.days_before * 86400)
                    and (args.tag_days_after is None or txtmtime != 0 and txtmtime > now - args.tag_days_after * 86400)
                    and (args.tag_days_before is None or txtmtime != 0 and txtmtime > now - args.tag_days_before * 86400)):
            if args.verbose:
                print(f'Target png file: {file} (modified {math.floor((now - pngmtime) / 864) / 100} days before)')
                if txtmtime != 0:
                    print(f'Target tag file: {os.path.basename(txtfile_path)} (modified {math.floor((now - txtmtime) / 864) / 100} days before)')
            files.append(pngfile_path)

prompts = []
tags = []
sp = []

print(f'Parsing {len(files)} files')
for file in tqdm(files):
    if args.prompt:
        img = Image.open(file)
        if 'parameters' in img.text:
            splited = re.split(r'\s*[,\n]\s*', img.text['parameters'])
            words = []
            for sp in splited:
                if sp.startswith('Negative prompt:'):
                    break
                words.append(re.sub(r'(^\s*\(\s*|\s*\)\s*$|\:[\d\.]+\)$)', '', sp))
            words = [e.lower() for e in words if e != 'BREAK']
            prompts.append(words)
        else:
            prompts.append([])
    if args.tag:
        txtfile = re.sub(r'\.png$', '.txt', file)
        if os.path.isfile(txtfile):
            with open(txtfile, 'r') as f:
                tags.append(re.split(r'\s*,\s*', f.readline().replace('_', ' ')))
        else:
            tags.append([])

if args.prompt and len(files) != len(prompts) or args.tag and len(files) != len(tags):
    print('Unexpected error occurred')
    sys.exit()

roots = ET.Element('XnView_Catalog', {'version': '1.0'})
fl = ET.SubElement(roots, 'FileList')
print(f'Preparing XML for {len(files)} files')
for index, file in enumerate(tqdm(files)):
    f = ET.SubElement(fl, 'File', {'filename': file.replace('\\', '/')})
    if args.prompt:
        for key in prompts[index]:
            if len(key):
                k = ET.SubElement(f, 'Keywords')
                k.text = 'prompts|' + key.strip()
    if args.tag:
        for key in tags[index]:
            if len(key):
                k = ET.SubElement(f, 'Keywords')
                k.text = 'tags|' + key.strip()
    if args.categoly is not None:
        for key in args.categoly:
            if len(key):
                k = ET.SubElement(f, 'Keywords')
                k.text = key.strip()

if args.no_generation:
    sys.exit()

print('Generating XML')
doc = md.parseString(ET.tostring(roots, 'utf-8'))
with open(args.output if args.output else 'XnView_Catalog.xml', 'w') as f:
    doc.writexml(f, encoding='UTF-8', newl='\n', indent='', addindent='    ')
print('Done')
