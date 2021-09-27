import os
import hashlib
from pathlib import Path
GIT_DIR = ".dagit"
OBJ_DIR = GIT_DIR +"/objects/"

def init():
    os.makedirs(GIT_DIR)
    os.makedirs(OBJ_DIR)


def hash_obj(data, type='blob'):
    obj= type.encode() + b'\x00' + data
    goid= hashlib.sha1(obj).hexdigest() # goid = Git Object ID
    with open (OBJ_DIR + goid, 'wb') as out:
        out.write (obj)
    return goid

def get_obj(goid, expected='blob'):
    with open (OBJ_DIR + goid, 'rb') as file: #was OBJ_DIR
        obj = file.read()

    type, empty , data = obj.partition(b'\x00')
    type=type.decode()

    if expected is not None and type != expected:
        raise ValueError(f'Expected: {expected}, but got: {type}')
    return data
"""
def set_HEAD(goid):
    with open (GIT_DIR + "/HEAD", 'w') as file:
        file.write(goid)

def get_HEAD():
    if os.path.isfile(GIT_DIR + "/HEAD"):
        with open (GIT_DIR + "/HEAD") as file:
            return file.read().strip()
"""
def update_ref(ref,goid):
    ref_path= GIT_DIR+'/'+ref
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open (ref_path, 'w') as file:
        file.write(goid)

def get_ref(ref):
    ref_path= GIT_DIR+'/'+ref
    if os.path.isfile(ref_path):
        with open (ref_path) as file:
            return file.read().strip()

def iter_refs():
    refs=['HEAD']
    for root, _, filenames in os.walk(GIT_DIR+'/refs'):
        root= os.path.relpath(root, GIT_DIR)
        refs.extend(root+'/' + name for name in filenames)

    for ref in refs:
        yield ref, get_ref(ref)
