from pathlib import Path
import shutil
import filecmp
import argparse
import logging
from datetime import datetime as dt
import sched,time

s = sched.scheduler(time.time, time.sleep)


def print_time(a="default"):
    print("Executing: ", time.time(), a)

def printQueue():
    logging.info(time.ctime())
    print(time.time())

    s.enter(10, 1, print_time)
    s.enter(5, 2, print_time, argument=('positional',))
    s.enter(5, 1, print_time, kwargs={'a': 'keyword'})
    s.run()
    print(time.time())

printQueue()


def makeSchedule():
    pass

def makeLogger(logPath):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)-4.6s] [%(levelname)-5.5s]  %(message)s %(args)s",
        handlers=[logging.FileHandler(f"{logPath}/log.log"),logging.StreamHandler()]
        )
    return logging


# 1. Synchronization must be one-way: after the synchronization content of the replica folder
# should be modified to exactly match content of the source folder;
# 2. Synchronization should be performed periodically;
# 3. File creation/copying/removal operations should be logged to a file and to the console
# output;
# DONE: Folder paths, synchronization interval and log file path should be provided using the
# command line arguments.


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
        return p

def mkPath(path):
    p = Path(path)
    if not p.exists():
        p.mkdir()
        logging.info(f"Directory {p} created")
        return p
    elif p.is_dir():
        return p
    
def makeParser():
    parser = argparse.ArgumentParser()
    parser.add_help = True
    parser.add_argument("-l", "--logPath", action="store",
                         type=validPath,default=Path.cwd())
    parser.add_argument("-s", "--syncInterval", help="Sync interval in seconds",
                        action="store", type=checkInt,default=60)
    parser.add_argument("-o", "--origin", help="Path to original folder",
                        action="store", required=True,  type=validPath)
    parser.add_argument("-r", "--replica", help="Path to replica folder",
                        action="store", required=True, dest="replica", type=mkPath)
    return parser


def cmp(dir1, dir2):
    comp = filecmp.dircmp(dir1, dir2)
    return comp

def main(args):
    ac = actionCount = 0
    orig = Path(args.origin).resolve()
    repl = Path(args.replica).resolve()
    oStat,rStat = orig.stat(),repl.stat()
    lastSync = rStat.st_mtime_ns
    comp = cmp(orig,repl)
    if comp.left_only: ### Check which files 
        left = comp.left_only
        logging.warning(f"{len(left)} new file(s) found in {orig} ")
        for n,f in enumerate(left):
            src = orig.joinpath(f)
            dest = shutil.copy2(src,repl)
            logging.info(
            f"# {n} {f} created in {comp.left} on {dt.fromtimestamp(src.stat().st_ctime).isoformat(sep=' ')} ")
    if comp.right_only:
        r = comp.right_only
        logging.warning(f"{len(r)} files removed from {orig}.")
        for f in r:
            f = repl.joinpath(f)
            f.unlink()
            logging.info(f"Deleted {f.name} from {repl}")

    if oStat.st_mtime_ns > lastSync:
        logging.info("Synchronizing")
        for n,f in enumerate(orig.iterdir()):
            shutil.copy2(f,repl)
            logging.info(f"#{n} Created {f.name} in {repl}")
    if not cmp(orig,repl).diff_files:
        logging.info(f"Sync completed")
    return comp


def interval(interval=args.sync):
    pass


if __name__ == "__main__":
    parser = makeParser()
    args = parser.parse_args()
    logging = makeLogger(args.logPath)
    sync = main(args)
    if sync.diff_files:
        rep = sync.report()
    else:
        logging.info("Folders synchronized")
