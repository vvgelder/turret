import os
import sys
from distutils.util import strtobool
import tempfile
from subprocess import call

def editor(text):
    EDITOR = os.environ.get('EDITOR','vi')
    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmpf:
        tmpf.write(text)
        tmpf.flush()
        call([EDITOR, tmpf.name])
        return tmpf.name

def remove(filename):
    os.remove(filename)

def yesno(question):
    sys.stdout.write('%s [y/n]: ' % question)
    while True:
        try:
            return strtobool(raw_input().lower())
        except ValueError:
            sys.stdout.write('Please respond with \'y\' or \'n\'.\n')
