# Version: 0.1.1
import os
import sys
import argparse
from PIL import Image
from PIL.PngImagePlugin import PngInfo

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('png', nargs='*', help='png file')
parser.add_argument('-p', '--python', action='store_true', help='show path of python executable binary')
parser.add_argument('-l', '--link', action='store_true', help='show link strings for windows shortcut')
args = parser.parse_args()

if args.python:
    print(sys.executable)
    sys.exit()

if args.link:
    print('"' + sys.executable + '" "' + os.path.abspath(__file__) + '"')
    sys.exit()

if len(args.png) == 0:
    print('Specify png file')
    sys.exit()

path = ' '.join(args.png)

if not (os.path.isfile(path) and path.endswith('.png')):
    print('Specified path is not png file')
    sys.exit()

metadata = PngInfo()
img = Image.open(path)

for key in img.text:
    if not key == 'memo':
        metadata.add_text(key, img.text[key])

print('Please type your note and press Enter (double-byte characters are not allowed)')
metadata.add_text('memo', input('>> '))

img.save(path, pnginfo=metadata)
