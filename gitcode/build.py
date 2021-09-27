import os
import hashlib
from pathlib import Path
from collections import namedtuple
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





def iter_refs(prefix='',deref=True):
    refs=['HEAD']
    for root, _, filenames in os.walk(GIT_DIR+'/refs'):
        root= os.path.relpath(root, GIT_DIR)
        refs.extend(root+'/' + name for name in filenames)

    for ref in refs:
        if not ref.startswith(prefix):
            continue
        yield ref, get_ref(ref, deref=deref)
