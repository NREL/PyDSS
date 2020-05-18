import shutil
import sys
import os

dirName = r'C:\Users\alatif\Desktop\PyDSS_2.0\PyDSS\examples'

'''
    Get a list of empty directories in a directory tree
'''

# Create a List
listOfEmptyDirs = list()

# Iterate over the directory tree and check if directory is empty.
for (dirpath, dirnames, filenames) in os.walk(dirName):
    if len(dirnames) == 0 and len(filenames) == 0:
        listOfEmptyDirs.append(dirpath)

# Iterate over the empty directories and print it
for elem in listOfEmptyDirs:
    print(elem)

print("****************")

listOfEmptyDirs = [dirpath for (dirpath, dirnames, filenames) in os.walk(dirName) if
                   len(dirnames) == 0 and len(filenames) == 0]

file = os.path.join(dirName, "null.txt")

for elem in listOfEmptyDirs:
    target = os.path.join(elem, "null.txt")
    shutil.copyfile(file, target)