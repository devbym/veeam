from filecmp import dircmp
from pathlib import Path
import shutil
import filecmp
import argparse
import logging
from datetime import datetime as dt
import sched
import time


def makeLogger(logPath):
    root = logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s l#[%(lineno)s] [%(levelname)-4.7s]  %(message)s %(args)s",
        handlers=[logging.FileHandler(
            f"{logPath}/log.log"), logging.StreamHandler()],
        encoding="utf-8"
    )
    return logging.getLogger(root)


# 1. Synchronization must be one-way: after the synchronization content of the replica folder
# should be modified to exactly match content of the source folder;
"""QUESTION: DOES THE CONTENT OF THE FOLDER CONTAIN ONLY FILES OR ALSO FOLDERS"""
# 2. Synchronization should be performed periodically;
"""INPUT = SYNC INTERVAL"""
# 3. File creation/copying/removal operations should be logged to a file and to the console
# output;

# DONE: Folder paths, synchronization interval and log file path should be provided using the
# command line arguments.
"""Folder paths"""


# TODO SYNC: check mtime on origin and only update if the mtime is different

def checkInt(value):
    if int(value) <= 0:
        logging.exception("%s is invalid: positive value required" % value)
        raise argparse.ArgumentTypeError(
            "%s is invalid: positive value required" % value)
    else:
        return int(value)

def validPath(path):
    p = Path(path)
    if not p.is_dir():
        raise argparse.ArgumentTypeError(
            "%s is invalid: not a directory" % path)
    else:
        return p.resolve()

def mkPath(path):
    p = Path(path)
    if not p.exists():
        p.mkdir()
        logging.info(f"Directory {p} created")
        return p
    elif p.is_dir():
        return p.resolve()

def makeParser():
    parser = argparse.ArgumentParser()
    parser.add_help = "Specify 1: path to origin folder and 2: path to the replica"
    parser.add_argument("-o", "--origin", help="Path to source folder",
                        action="store", required=True,  type=validPath)
    parser.add_argument("-r", "--replica", help="Path to replica folder", default="./replica",
                        action="store", required=True, type=mkPath)
    parser.add_argument("-l", "--logPath", action="store", help="Directory for logfile. Default is Path.cwd()",
                        type=validPath, default=Path.cwd())
    parser.add_argument("-i", "--interval", help="Sync interval in seconds",
                        action="store", type=checkInt, default=30)
    return parser


def getTime(t):
    return dt.fromtimestamp(t).isoformat(sep=' ')


# Recursive dircmp


def compare(dcmp):
    for name in dcmp.left_only:
        logging.info("File %s only found in %s" % (name, dcmp.left))
        if Path().is_dir(name):

            print("make path")
    for sub_dcmp in dcmp.subdirs.values():
        print(sub_dcmp)
        sub = cmp()
        compare(sub)


def newTree(dir1,dir2):
    try:
        shutil.rmtree(dir2)
        shutil.copytree(dir1,dir2)
    except:
        return
#dcmp = cmp("/Users/michiel/Desktop/Pictures", "replica")

# compare(dcmp)

# Recursive END

def syncQueue(s:sched.scheduler,args):
    #s.enter(args.interval,2,newTree,[args.origin, args.replica])
    s.enter(args.interval, 1, sync, [args.origin, args.replica])
    s.run()
    if s.empty():
        syncQueue(s,args)


def cmp(dir1: Path, dir2: Path):  # THIS FUNCTION SHOULD BE CALLED IN RECURSION
    comp = filecmp.dircmp(dir1, dir2)
    return comp


def shCopy(src:Path, dest:Path):
    try:
        cp = shutil.copy2(src, dest)
        logging.info(f"{src.name} created in {cp} on")
        return dest
    except IsADirectoryError as isdir:
        logger.info(f"Found new subdirectory: [{isdir.filename}]")
        try:
            #mkPath(isdir.filename)
            cp = shutil.copytree(isdir.filename, dest)
            logger.info(f"Copied subdirectory {src} to {cp}")
            return dest
        except Exception as e:
            logger.exception(e)
            return e.filename
            #sync(src, e.filename)s

def isSynced(dir1:Path,dir2:Path):
    if dir1.stat().st_mtime_ns > dir2.stat().st_mtime_ns:  # Check if modified time of original folder is greater than replica
        return False
    elif dir1.stat().st_mtime <= dir2.stat().st_mtime_ns:
        return True

def sync(dir1: Path, dir2: Path):
    comp = cmp(dir1, dir2)
    left, right = comp.left_only, comp.right_only
    if left:
        logger.info(f"{len(left)} file(s) found in {dir1}.")
    for f in left:
        src = dir1.joinpath(f)
        dest = dir2.joinpath(f)
        logger.info(f"Source: {src}, Dest: {dest}")
        if src.is_dir():
            if not dest.exists():
                mkPath(dest)
                sync(src,dest)
            elif dest.is_dir():
                if not isSynced(src,dest):
                    logger.warning(f"Not synced: {dest}")
                    sync(src,dest)
        if not dest.exists():
            shCopy(src,dest)
        else:
            try:
                shCopy(src, dest)
            except Exception as e:
                logger.warning(f"{e}")
                print(e.filename2)
                raise
    for f in right:
        src = dir1.joinpath(f)
        rmv = dir2.joinpath(f)
        logger.warning(f"Removing {rmv} from {dir2}")
        try:
            rmv.unlink()
        except PermissionError as e:
            logger.error(f"{e}")
            try:
                rmv.rmdir()
                logger.info(f"Deleted {rmv} from {dir2}")
            except OSError:
                shutil.rmtree(dir2)
                logger.info(f"Removed {dir2}")


def main(args):
    try:
        s = sched.scheduler(time.time, time.sleep)
        logger.info(f"Scheduler started at {time.ctime()}")
        syncQueue(s,args)
    except Exception as e:
        print(f"Exception occured: {e}")
        raise e
    return


if __name__ == "__main__":
    parser = makeParser()
    args = parser.parse_args()
    logger = makeLogger(args.logPath)
    main(args)
    #sync = main(args)
