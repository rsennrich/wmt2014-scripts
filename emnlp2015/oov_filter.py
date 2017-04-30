# filter out all phrases in a phrase table that contain words that are not in
# the provided vocabulary file

# usage: python oov_filter.py vocabulary_file < phrase_table_in > phrase_table_out

import sys

vocab = open(sys.argv[1]).readlines()
vocab = set([item.strip() for item in vocab])

discarded = open('discarded','w')

count = 0
dcount = 0
for line in sys.stdin:
    count += 1
    linesplit = line.split('|||')
    for word in linesplit[1].split()[:-1]:
      if word.startswith('['):
        continue
      elif word not in vocab:
        discarded.write(line)
        dcount += 1
        break
    else:
        print line,

sys.stderr.write('{0} out of {1} lines discarded\n'.format(dcount, count))
