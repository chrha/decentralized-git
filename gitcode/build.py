import os
import hashlib
from pathlib import Path
from collections import namedtuple
from contextlib import contextmanager
import shutil
import json
import subprocess




# Will be initialized in cli.main()
GIT_DIR = None

@contextmanager
def get_index ():
    index = {}
    if os.path.isfile (f'{GIT_DIR}/index'):
        with open (f'{GIT_DIR}/index') as f:
            index = json.load (f)

    yield index

    with open (f'{GIT_DIR}/index', 'w') as f:
        json.dump (index, f)



@contextmanager
def change_git_dir (new_dir):
    global GIT_DIR
    old_dir = GIT_DIR
    GIT_DIR = f'{new_dir}/.dagit'
    yield
    GIT_DIR = old_dir


def init():
    os.makedirs(GIT_DIR)
    os.makedirs(GIT_DIR +"/objects/")


def hash_obj(data, type='blob'):
    obj= type.encode() + b'\x00' + data
    goid= hashlib.sha1(obj).hexdigest() # goid = Git Object ID
    with open (GIT_DIR +"/objects/" + goid, 'wb') as out:
        out.write (obj)
    return goid

def get_obj(goid, expected='blob'):
    with open (GIT_DIR +"/objects/" + goid, 'rb') as file: #was OBJ_DIR
        obj = file.read()

    type, empty , data = obj.partition(b'\x00')
    type=type.decode()

    if expected is not None and type != expected:
        raise ValueError(f'Expected: {expected}, but got: {type}')
    return data

RefValue= namedtuple("RefValue",["symbolic", "value"])

def update_ref(ref,value, deref=True):
    ref = _get_ref_internal(ref,deref)[0]
    assert value.value
    if value.symbolic:
        value= "ref: " + value.value
    else:
        value= value.value
    ref_path= GIT_DIR+'/'+ref
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open (ref_path, 'w') as file:
        file.write(value)

def get_ref(ref,deref=True):
    return _get_ref_internal(ref,deref)[1]


def _get_ref_internal(ref,deref):
    ref_path= GIT_DIR+'/'+ref
    value=None
    if os.path.isfile(ref_path):
        with open (ref_path) as file:
            value = file.read().strip()
    symbolic= bool(value) and value.startswith("ref:")

    if symbolic:
        value= value.split(':',1)[1].strip()
        if deref:
            return _get_ref_internal(value, deref=True)
    return ref,RefValue(symbolic=symbolic, value=value)


def delete_ref (ref, deref=True):
    ref = _get_ref_internal (ref, deref)[0]
    os.remove (f'{GIT_DIR}/{ref}')


def iter_refs(prefix='',deref=True):
    refs = ['HEAD', 'MERGE_HEAD']
    for root, _, filenames in os.walk(GIT_DIR+'/refs'):
        root= os.path.relpath(root, GIT_DIR)
        refs.extend(root+'/' + name for name in filenames)

    for ref in refs:
        if not ref.startswith(prefix):
            continue
        r = get_ref (ref, deref=deref)
        if r.value:
            yield ref, r

def object_exists (oid):
    return os.path.isfile (f'{GIT_DIR}/objects/{oid}')


def fetch_object_if_missing (goid, remote_git_dir):
    if object_exists (goid):
        return
    remote_git_dir += '/.dagit'
    shutil.copy (f'{remote_git_dir}/objects/{goid}', #ändra senare
                 f'{GIT_DIR}/objects/{goid}')

def push_object (oid, remote_git_dir):
    #remote_git_dir += '.dagit' # ändrade här
    shutil.copy (f'{GIT_DIR}/objects/{oid}',
                 f'{remote_git_dir}/objects/{oid}')


def send_commit(oids, ref, deref=True):
    ref_i = _get_ref_internal(ref,deref)[0]
    ref_path= GIT_DIR+'/'+ref_i
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)

    with open(ref_path, 'rb') as f:
        data= f.read().decode()
    payload = {
        "ref": ref,
        "body": data
    }

    for goid in oids:
        with open(f"{GIT_DIR}/objects/{goid}", 'rb') as f:
            data= f.read().decode()
        payload[goid] = data
    
    command= f"python3 ../../ddagb/client.py \'{json.dumps(payload)}\'"

    os.system(command)

def isType(obj, type):
    with open (GIT_DIR +"/objects/" + obj, 'rb') as file: #was OBJ_DIR
        obj = file.read()

    t, empty , data = obj.partition(b'\x00')
    t = t.decode()
    return t == type
