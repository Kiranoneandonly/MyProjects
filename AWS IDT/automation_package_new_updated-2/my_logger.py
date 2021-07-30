import sys

sys.stdout = open('log.txt', 'w')

for c in (sys.argv[1:]):
    print(str(c))