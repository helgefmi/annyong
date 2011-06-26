import re

contents = open('nfac.t', 'r').read()
print re.compile('(^test.*)', re.MULTILINE).findall(contents)
