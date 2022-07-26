from pathlib import Path
import shutil
import filecmp
import argparse
import logging
from datetime import datetime as dt
import sched,time

s = sched.scheduler(time.time, time.sleep)

def makeLogger(logPath):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-4.7s]  %(message)s %(args)s",
        handlers=[logging.FileHandler(f"{logPath}/log.log"),logging.StreamHandler()]
        )
    return logging.getLogger()


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
    parser.add_help = "Specify 1: path to origin folder and 2: path to the replica"
    parser.add_argument("-o", "--origin", help="Path to source folder",
                        action="store", required=True,  type=validPath)
    parser.add_argument("-r", "--replica", help="Path to replica folder",default=Path("./replica"),
                        action="store", required=True, type=mkPath)
    parser.add_argument("-l", "--logPath", action="store",help="Directory for logfile. Default is Path.cwd()",
                         type=validPath,default=Path.cwd())
    parser.add_argument("-i", "--interval", help="Sync interval in seconds",
                        action="store", type=checkInt,default=30)
    return parser

def getTime(t):
    return dt.fromtimestamp(t).isoformat(sep=' ')


def check(src,dest):
    comp = cmp(src,dest)
    dif = comp.left_only
    message = (f"Comp: {dif} ", str(time.time()), str(src) , str(dest))
    logger.info(message)

def syncQueue(args):
    sync = args.interval
    tt = time.time
    logging.info(tt())
    logging.info(f"Scheduler started at {time.ctime()}")
    s.enter(sync,2,cmp,[args.origin,args.replica])
    s.enter(sync,1,main,[args])
    s.enter(5, 2, check,[args.origin,args.replica])
    #s.enter(sync,1,check,[args.origin])
    s.run()
    if s.empty():
        syncQueue(args)


def cmp(dir1:Path, dir2:Path):
    comp = filecmp.dircmp(dir1, dir2)
    return comp

def main(args):
    orig = Path(args.origin).resolve()
    repl = Path(args.replica).resolve()
    oStat,rStat = orig.stat(),repl.stat()
    lastSync = rStat.st_mtime_ns
    comp = cmp(orig,repl)
    left,right = comp.left_only,comp.right_only
    if left: ### Check which files are in original folder only
        logger.warning(f"{len(left)} new file(s) found in {orig} ")
        for n,f in enumerate(left):
            src = orig.joinpath(f)
            dest = shutil.copy2(src,repl)
            logging.info(
            f"# {n} {dest} created in {comp.left} on {dt.fromtimestamp(src.stat().st_ctime).isoformat(sep=' ')} ")
    if right:
        logging.warning(f"{len(r)} files removed from {orig}.")
        for f in right:
            rmv = repl.joinpath(f)
            rmv.unlink()
            logging.info(f"Deleted {f.name} from {repl}")

    if oStat.st_mtime_ns > lastSync:
        logging.info("Synchronizing")
        for n,f in enumerate(orig.iterdir()):
            shutil.copy2(f,repl)
            logging.info(f"#{n} Created {f.name} in {repl}")
    if not cmp(orig,repl).diff_files:
        logger.info(f"Sync completed")
    return comp


if __name__ == "__main__":
    parser = makeParser()
    args = parser.parse_args()
    logger = makeLogger(args.logPath)
    que = syncQueue(args)
    sync = main(args)
    if sync.diff_files:
        rep = sync.report()
    else:
        logger.info("Folders synchronized")
