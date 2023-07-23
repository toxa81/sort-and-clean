import os
import hashlib
import glob
import time
import argparse
import sys

#def callback(arg, directory, files):
#    for file in files:
#        print os.path.join(directory, file), repr(arg)
#
#os.path.walk(".", callback, "secret message")

parser = argparse.ArgumentParser(description='Sort folders and find duplicates')
#parser.add_argument('DIR', help='Directory with the test')
parser.add_argument('-i', '--input', help='Input folder (won\'t be modified)')
parser.add_argument('-o', '--output', help='Output folder')
parser.add_argument('-a', '--action', help='Do one of the following actions: dry run, copy files, move files', default='dry', choices=["dry", "copy", "move"])
parser.add_argument('-d', '--date', action='store_true', help='Move/copy files to final destination folder based on their date stamps')
parser.add_argument('-e', '--ext', help='Allowed file extensions', nargs="+", type=str, default=['jpg', 'jpeg', 'dng'])
args = parser.parse_args()

if len(sys.argv) < 4:
    parser.print_help()
    sys.exit(0)

dry_run = args.action == 'dry'
input_folder = os.path.normpath(args.input)
output_folder = os.path.normpath(args.output)

file_extensions = ['*'] if args.ext[0] == '*' else [f".{e}" for e in args.ext]

print(f"{file_extensions}")

if dry_run:
    print(f"Warning! This is a dry run and no real action will be performed!")
    
print("Sorting files into folders")
print(f"Input root folder  : {input_folder}")
print(f"Output folder      : {output_folder}")
print(f"Add date stamp     : {args.date}")

def md5hash(fname):
    md5h = hashlib.md5()
    with open(fname, "rb") as f:
        for byte_block in iter(lambda: f.read(4096),b""):
            md5h.update(byte_block)
    return md5h.hexdigest()

# def compare_two_files(fname1, fname2):

#     md5_1 = hashlib.md5()
#     md5_2 = hashlib.md5()

#     with open(fname1, "rb") as f1:
#         with open(fname2, "rb") as f2:
#             while True:
#                 data1 = f1.read(1024)
#                 data2 = f2.read(1024)
#                 if not data1: break
#                 md5_1.update(data1)
#                 md5_2.update(data2)

#                 if md5_1.digest() != md5_2.digest():
#                     return False

#     return True

# def inspect_group_of_files(fsize, files):

#     duplicate_size = 0
#     eq_files = {}

#     # groups of files
#     fgroup = [0 for i in range(len(files))]
    
#     igroup = 0
#     for i in range(len(files)):
#         # if this file was not checked
#         if fgroup[i] == 0:
#             igroup += 1
#             # this file receives a new group
#             fgroup[i] = igroup

#             eq_files.setdefault(igroup, []).append(files[i])
#             # inspect other files
#             for j in range(i + 1, len(files)):
#                 if fgroup[j] == 0 and compare_two_files(files[i], files[j]):
#                     fgroup[j] = fgroup[i]
#                     eq_files.setdefault(igroup, []).append(files[j])
    
#     for key in eq_files:
#         if (len(eq_files[key]) > 1):
#             duplicate_size += fsize * (len(eq_files[key]) - 1)
#             print("=== duplicate files of size: %.4f M ==="%(fsize / 1024 / 1024))
#             for f in eq_files[key]:
#                 print("  " + f)
    
#     return duplicate_size

# step 1: starting from a root folder, find equal files
# make list of groups; group is a set of equal fils
# Q: how to identify the creation/modification time?
#   get all, then compare

# step 2: move one of equal files to the proper location in target directory

# step 3: move other duplicates into staging folder preserving the path

def file_date_stamp(f):
    t = time.gmtime(min(os.path.getmtime(f), os.path.getctime(f)))
    return str(t.tm_year) + '-' + str(t.tm_mon).zfill(2) + '-' + str( t.tm_mday).zfill(2)

def process_equal_size_files(files):
    file_groups = {}
    # loop over all atoms of the same size and split them into subgroups using hash as key
    for f in files:
        label = file_date_stamp(f)
        file_groups.setdefault(md5hash(f), []).append({'file' : f, 'label' : label})

    # loop over subgroups
    # each file in the subgroup has the same hash (files are equal)
    # still, files might have a different creation time
    for h in file_groups:
        lref = ''
        consistent = True
        labels = []
        for e in file_groups[h]:
            if lref == '': lref = e['label']
            if (e['label'] != lref): consistent = False
            labels.append(e['label'])

        if consistent:
            print("file group is consistent")
        else:
            print("file group is not consistent", labels)

def process_single_file(file):
    # get name of the file from full path
    fpath, fname = os.path.split(file)
    # destination file name relative to output_folder
    file_out = "/" + file_date_stamp(file) + "/" + fname if args.date else file[len(input_folder):]
    file_out = output_folder + file_out
    print(f"{file} => {file_out}")
    os.makedirs(os.path.dirname(file_out), exist_ok=True)
    #shutil.copy(src_fpath, dest_fpath)


def main():
    equal_size_files = {}
    # find all files recursively and add them to the dictionary
    # file size is the key of that dictionary
    for f in glob.iglob(f"{args.input}/**", recursive=True):
        file_name, file_extension = os.path.splitext(f)
        if file_extensions[0] == '*' or file_extension.lower() in file_extensions:
            size = os.path.getsize(f)
            # append file to the list of files with the same sizes
            equal_size_files.setdefault(size, []).append(f)

            #t = time.gmtime(min(os.path.getmtime(f), os.path.getctime(f)))
            #print(t.tm_year, t.tm_mon, t.tm_mday)
    print(f"All files are scanned; size of the dictionary: {len(equal_size_files)}")
    #
    # perform the final acition
    #
    for key in equal_size_files:
        # this is a group of files
        if len(equal_size_files[key]) > 1 and key != 0: 
            process_equal_size_files(equal_size_files[key])
        else: # this is a single file
            process_single_file(equal_size_files[key][0])
    
#    print("total size of duplicates: %.4f M"%(duplicate_size / 1024 / 1024));
#    print("%i files inspected"%nfiles)
#    print("%i files listed"%nfiles_tot)

if __name__ == "__main__":
    main()

