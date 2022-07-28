from pathlib import Path
import shutil
import filecmp
import argparse
import logging
from datetime import datetime as dt
import sched
import time

def makeLogger(logPath):
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s #[%(lineno)s] [%(levelname)-4.7s]  %(message)s %(args)s",
        handlers=[logging.FileHandler(
            f"{logPath}/log.log"), logging.StreamHandler()],
        encoding="utf-8"
    )
    return logging.getLogger()

def checkInt(value) -> int:
    if int(value) <= 0:
        logging.exception(f"{value} is invalid: Should be > 0")
        raise argparse.ArgumentTypeError(
            f"{value} is invalid: positive value required")
    else:
        return int(value)

def validPath(path):
    p = Path(path)
    if not p.is_dir():
        raise argparse.ArgumentTypeError(
            f"{path} is invalid: not a directory")
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


def newTree(dir1:Path,dir2:Path):
    try:
        shutil.rmtree(dir2)
        logger.info(f"Removed tree {dir2}")
        shutil.copytree(dir1,dir2)
        logger.info(f"Copied tree {dir1}")
    except FileNotFoundError:
        pass
    except Exception as e:
        raise e



def sQueue(s:sched.scheduler,args):
    #s.enter(args.interval,1,newTree,[args.origin, args.replica])
    s.enter(args.interval,1, sync, [args.origin, args.replica])
    s.run()
    if s.empty():
        logger.info("Running sync...")
        sQueue(s,args)
        return 
    else:
        return False
        


def cmp(dir1: Path, dir2: Path):  # THIS FUNCTION SHOULD BE CALLED IN RECURSION
    comp = filecmp.dircmp(dir1, dir2)
    return comp


def fCopy(src:Path, dest:Path):
    try:
        shutil.copy2(src, dest,)
        logging.info(f"{src.name} created in {dest} on")
        return dest
    except IsADirectoryError as isdir:
        logger.info(f"Found directory: [{isdir.filename}]")
        dCopy(src,dest)

def dCopy(src:Path, dest:Path):
    try:
        shutil.copytree(src, dest,dirs_exist_ok=True)
        logger.info(f"Copied subdirectory {src} to {dest}")
        return dest
    except FileNotFoundError as e:
        logger.exception(e)
        newTree(src,dest)

def isSynced(dir1:Path,dir2:Path):
    if dir1.stat().st_mtime_ns < dir2.stat().st_mtime_ns: # Check if modified time of original folder is greater than replica
        return False  
    else:
        return True



def sync(dir1: Path, dir2: Path):
        comp = cmp(dir1, dir2)
        left, right = comp.left_only, comp.right_only
        for f in dir1.iterdir():
            src = dir1.joinpath(f.name)
            dest = dir2.joinpath(f.name)
            if src.is_dir():
                if dest.is_dir():
                    if not dest.exists():
                        dCopy(src,dest)
                    if not isSynced(dir1,dir2):
                        sync(src,dest)
        if left:
            logger.info(f"{len(left)} new file(s) found in {dir1.name}.")
            for f in left:
                src = dir1.joinpath(f)
                dest = dir2.joinpath(f)
                fCopy(src,dest)
        if right:
            for f in right:
                src = dir1.joinpath(f)
                rmv = dir2.joinpath(f)
                logger.info(f"File {rmv.name} was removed from {dir1}")
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
                    except:
                        raise
                except FileNotFoundError:
                    pass


def main(args):
    try:
        s = sched.scheduler(time.time, time.sleep)
        logger.info(f"Scheduler started at {time.ctime()}")
        sQueue(s,args)
    except RecursionError:
        logger.info(f"Recursion limit reached. Scheduler restarted at {time.ctime()}")
        main(args())
    except FileNotFoundError as fn:
        if fn.filename == 'replica':
            mkPath(args.replica)
            logger.warning(f"Replica folder was removed!\n Created folder ./{args.replica} \nScheduler restarted at {time.ctime()}")
        main(args)


if __name__ == "__main__":
    parser = makeParser()
    args = parser.parse_args()
    logger = makeLogger(args.logPath)
    main(args)
