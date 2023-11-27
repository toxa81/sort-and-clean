import os
import hashlib
import glob
import time
import argparse
import sys
import re
import shutil

parser = argparse.ArgumentParser(description='Sort folders and find duplicates')
#parser.add_argument('DIR', help='Directory with the test')
parser.add_argument('-i', '--input', help='Input folder (modified in case files are moved out of it)')
parser.add_argument('-o', '--output', help='Output folder')
parser.add_argument('-a', '--action', help='Do one of the following actions: dry run, copy files, move files', default='dry', choices=["dry", "copy", "move"])
parser.add_argument('-d', '--dupe', action='store_true', help='Sort only duplicates')
parser.add_argument('-s', '--sort', action='store_true', help='Move/copy files to YYYY-MM-DD/file-name instead of a full path')
parser.add_argument('-e', '--ext', help='Allowed file extensions', nargs="+", type=str, default=['jpg', 'jpeg', 'dng', 'mov', 'heic', 'pef', 'png', 'm4v', 'mp4', 'gif'])
parser.add_argument('-x', '--exclude', help='RegExp to exclude search path', default="")
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
print(f"Input folder   : {input_folder}")
print(f"Output folder  : {output_folder}")
print(f"Add date stamp : {args.sort}")

equal_files_group_id = 0


def equal_size_files_map(input_folder, file_extensions, exclude):
    """ Build a map of files of equal size.

    Key of the map is the file size and each element is a list of files of the same size.

    """

    equal_size_files = {}
    # find all files recursively and add them to the dictionary
    # file size is the key of that dictionary
    for f in glob.iglob(f"{input_folder}/**", recursive=True):
        # add files if there is not regexp or regexp is not matched
        if exclude == "" or not re.findall(exclude, f):
                file_name, file_extension = os.path.splitext(f)
                if  os.path.isfile(f) and (file_extensions[0] == '*' or file_extension.lower() in file_extensions):
                    size = os.path.getsize(f)
                    # append file to the list of files with the same sizes
                    equal_size_files.setdefault(size, []).append(f)

    # remove empty files from resulting dictionary
    equal_size_files.pop(0, None)
    return equal_size_files


def md5hash(fname):
    """ Compute md5 sum of the file """
    md5h = hashlib.md5()
    with open(fname, "rb") as f:
        for byte_block in iter(lambda: f.read(4096),b""):
            md5h.update(byte_block)
    return md5h.hexdigest()


# step 1: starting from a root folder, find equal files
# make list of groups; group is a set of equal fils
# Q: how to identify the creation/modification time?
#   get all, then compare

# step 2: move one of equal files to the proper location in target directory

# step 3: move other duplicates into staging folder preserving the path

def file_date_stamp(f):
    """ Get data stamp of the file in the form YYYY-MM-DD """
    t = time.gmtime(min(os.path.getmtime(f), os.path.getctime(f)))
    return str(t.tm_year) + '-' + str(t.tm_mon).zfill(2) + '-' + str( t.tm_mday).zfill(2)

def process_single_file(input_file, input_folder, output_folder, sort, action):
    """ Process a single file

    Single file exists only once in the input folder and its subfolders. Depending on the `sort` flag
    input file is copied or moved to output_folder/YYYY-MM-DD/file.name or output_folder/sub/path/to/file.name
    location.

    """
    # get name of the file from full path
    fpath, fname = os.path.split(input_file)
    # destination file name relative to output_folder
    output_file = "/" + file_date_stamp(input_file) + "/" + fname if sort else input_file[len(input_folder):]
    # compose either output_folder/YYYY-MM-DD/file.name or output_folder/local/path/to/file.name
    output_file = output_folder + output_file

    print(f"{input_file} => {output_file}")
    if (os.path.isfile(output_file)):
        print(f"{output_file} alredy exists!")
        sys.exit(0)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if action == "copy":
        shutil.copy(src_fpath, dest_fpath)
    if action == "move":
        shutil.move(input_file, output_file)


def process_equal_files(input_files, input_folder, output_folder, sort, action):
    """ Process the list of identical files """

    # find the file with shortest name
    shortest_file = None
    shortest_file_path = None
    for e in input_files:
        fpath, fname = os.path.split(e)
        if not shortest_file or len(fname) < len(shortest_file):
            shortest_file = fname
            shortest_file_path = e

    global equal_files_group_id
    print(f"Group {equal_files_group_id} of identical files:")
    for e in input_files:
        if e == shortest_file_path:
            process_single_file(e, input_folder, output_folder, sort, action)
        else:
            process_single_file(e, input_folder, output_folder + "/clones", sort, action)

    equal_files_group_id += 1

def process_files(size, files, dupe, input_folder, output_folder, sort, action):
    """ Process one or several files """

    file_groups = {}
    # loop over all files of the same size and split them into subgroups using hash as key
    for f in files:
        label = file_date_stamp(f)
        file_groups.setdefault(md5hash(f), []).append({'file' : f, 'label' : label})

    print(f"Number of files with size {size} is {len(files)}; split in {len(file_groups)} different group(s) by md5 hash")

    # loop over subgroups
    # each file in the subgroup has the same hash (files are equal)
    # still, files might have a different creation time
    for h in file_groups:

        labels = []
        files = []
        for e in file_groups[h]:
            labels.append(e['label'])
            files.append(e['file'])

        # if we only look for duplicates and this is a single file, slip it
        if dupe and len(labels) == 1:
            continue

        if len(set(labels)) == 1:
            process_equal_files(files, input_folder, output_folder, sort, action)
            # print("file group is consistent; identical files are:")
            # for e in files:
            #     #print(f"{e}")
            #     process_single_file(e)
        else:
            print("file group is not consistent")
            for (e, f) in zip(labels, files):
                print(f"{e} {f}")

        print("")

def main():
    equal_size_input_files = equal_size_files_map(args.input, file_extensions, args.exclude)
    equal_size_output_files = equal_size_files_map(args.output, ['*'], "")

    print(f"All files are scanned; size of the dictionary: {len(equal_size_input_files)}")
    print(f" -> size of the output dictionary: {len(equal_size_output_files)}")

    #
    # perform the final acition
    #
    for key in equal_size_input_files:
        process_files(key, equal_size_input_files[key], args.dupe, input_folder, output_folder, args.sort, args.action)

if __name__ == "__main__":
    main()

