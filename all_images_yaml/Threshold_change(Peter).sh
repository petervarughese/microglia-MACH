#!/usr/bin/python

import os

path = "/Users/petervarughese/Downloads/all_images_yaml"
onlyfiles = os.listdir(path)

#onlyfiles = [ f for f in listdir() if isfile(f) and str(f)[-5:]==".yaml" ]

for file in onlyfiles:
  with open(file, 'r') as f:
    d = f.read().replace('cellThres: 125','cellThres: 100')
  with open(file, 'w') as f:
    f.write(d)