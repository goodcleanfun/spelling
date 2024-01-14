import json
import math
import os
from collections import namedtuple
from foundational.download import download_file
from foundational.zip_archive import unzip_all_files

NOISY_TYPING_URL = "https://osf.io/download/sdb23"

NoisyQWERTYRecord = namedtuple('NoisyQWERTYRecord', ['device', 'experiment', 'set', 'condition', 'participant', 'input', 'expected'])


class NoisyQWERTY(object):
    def __init__(self, out_dir=None):
        if out_dir is None:
            out_dir = os.path.curdir
        self.out_dir = out_dir
        keyboards_file = os.path.join(out_dir, 'noisy_typing', 'json', 'keyboards.json')
        data_file = os.path.join(out_dir, 'noisy_typing', 'json', 'noisy_typing.json')
        if not os.path.exists(keyboards_file) or not os.path.exists(data_file):
            zip_file = self.download_data(out_dir)
            self.unzip_data(zip_file, out_dir)

        self.keyboard = self.keyboard_coordinates(keyboards_file)
        self.data = self.read_data(data_file)

    @classmethod
    def keyboard_coordinates(cls, keyboards_file):
        keyboards = {}
        keyboard_data = json.load(open(keyboards_file))
        for keyboard in keyboard_data:
            keys = {}
            name = keyboard['keyboard']
            for key in keyboard['keys']:
                c = key['character']
                if c == '<sp>':
                    c = ' '
                x = key['x_center']
                y = key['y_center']
                width = key['width']
                height = key['height']
                min_x = x - width / 2.0
                max_x = x + width / 2.0
                min_y = y - height / 2.0
                max_y = y + height / 2.0
                keys[c] = (min_x, max_x, min_y, max_y)
            keyboards[name] = keys
        return keyboards

    @classmethod
    def download_data(cls, out_dir=None):
        return download_file(NOISY_TYPING_URL, os.path.join(out_dir or os.path.curdir), "noisy_typing.zip")

    @classmethod
    def unzip_data(cls, zip_file, out_dir=None):
        return unzip_all_files(zip_file, out_dir or os.path.curdir)

    def key_at_coordinates(self, keyboard, x, y):
        keys = self.keyboard[keyboard]
        for k, v in keys.items():
            x_min, x_max, y_min, y_max = v
            if x >= x_min and x <= x_max and y >= y_min and y <= y_max:
                return k
        return None

    def closest_key(self, keyboard, x, y):
        keys = self.keyboard[keyboard]
        min_dist = float('inf')
        min_key = None

        for k, v in keys.items():
            x_min, x_max, y_min, y_max = v
            dist = math.sqrt((max(x_min - x, 0, x - x_max)) ** 2 + (max(y_min - y, 0, y - y_max)) ** 2)
            if dist < min_dist:
                min_dist = dist
                min_key = k
        return min_key

    def user_input(self, d):
        text = []
        keyboard = d['keyboard']
        chunks = d['chunks']
        for c in chunks:
            if c['deleted']:
                continue
            taps = c['taps']
            for tap in taps:
                t = tap['input'][0]
                x = t['x']
                y = t['y']
                k = self.key_at_coordinates(keyboard, x, y)
                if k:
                    text.append(k)
                else:
                    k = self.closest_key(keyboard, x, y)
                    if k:
                        text.append(k)
                    else:
                        text.append('#')
            if text and text[-1] != ' ':
                text.append(' ')
        return ''.join(text).strip()

    def read_data(self, data_file):
        data = json.load(open(data_file))
        return [NoisyQWERTYRecord(
            d['device'],
            d['experiment'],
            d['set'],
            d.get('condition'),
            d['participant'],
            self.user_input(d),
            d['ref']) for d in data if 'ref' in d]
