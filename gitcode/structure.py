import build
import os
import itertools
import operator
from collections import namedtuple
from pathlib import Path
import string

def write_tree(directory="."):
    entries = []
    with os.scandir(directory) as iter:
        for entry in iter:
            path= directory+'/'+entry.name
            if ignore(path):
                continue
            if entry.is_file(follow_symlinks=False):
                type="blob"

                with open(path, 'rb') as f:
                    goid = build.hash_obj(f.read())
            elif entry.is_dir(follow_symlinks=False):
                type="tree"
                goid=write_tree(path)
            entries.append((entry.name, goid,type))

    tree=''.join(type + ' ' + goid + ' ' + name + '\n'
                for name,goid,type in sorted(entries))
    return build.hash_obj(tree.encode(),"tree")


def iter_tree(goid):
    if not goid:
        return
    tree= build.get_obj(goid,"tree")
    tree=tree.decode()
    for elem in tree.splitlines():
        type,goid,name = elem.split(' ',2)
        yield type, goid, name

def get_tree(goid, start_path=''):
    res={}
    for type, goid, name in iter_tree(goid):
        assert '/' not in name
        assert name not in ('..', '.')
        path=start_path+name
        if type == 'blob':
            res[path]=goid
        elif type == 'tree':
            res.update(get_tree(goid, path + '/' ))
        else:
            raise ValueError("type is neither tree nor blob")
    return res

def empty_working_dir():
    for root,dirs,files in os.walk('.', topdown=False):
        for file in files:
            path= os.path.relpath(root+'/'+file)
            if ignore(path) or not os.path.isfile(path):
                continue
            os.remove(path)
        for dir in dirs:
            path= os.path.relpath(root+'/'+ dir)
            if ignore(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                 # If a dir contain an ignored file, then removing it
                # might fail, which is fine.
                pass


def read_tree(tree_goid):
    empty_working_dir()
    for path, goid in get_tree(tree_goid,start_path='./').items():
        os.makedirs(os.path.dirname(path), exist_ok=True)#make dir, if exists-> dont alter
        with open(path,"wb") as file:
            file.write(build.get_obj(goid))

def ignore(path):
    return ".dagit" in Path(path).parts


def commit(msg):
    commit= "tree " + write_tree() + "\n"
    parent= build.get_ref('HEAD')
    if parent:
        commit += "parent " + parent
    commit += "\n" + msg + "\n"
    obj = build.hash_obj(commit.encode(),"commit")
    build.update_ref('HEAD',obj)
    return obj


Commit = namedtuple ('Commit', ['tree', 'parent', 'message'])


def get_commit (goid):
    parent = None

    commit = build.get_obj (goid, 'commit').decode ()
    lines = iter (commit.splitlines ())
    for line in itertools.takewhile (operator.truth, lines):
        key, value = line.split (' ', 1)
        if key == 'tree':
            tree = value
        elif key == 'parent':
            parent = value
        if parent and tree:
            break

    message = '\n'.join (lines)

    return Commit (tree=tree, parent=parent, message=message)

def checkout(goid):
    commit = get_commit(goid)
    read_tree(commit.tree)
    build.update_ref('HEAD',goid)

def create_tag(name, goid):
    # create the tag later
    tag= "refs/tags/"+name
    build.update_ref(tag,goid)

def get_goid(name):
    #return build.get_ref(name) or name
    if name=='@':name='HEAD'
    # Name is a reference
    possible_refs = [
        name,
        "refs/" + name,
        'refs/tags/' + name,
        'refs/heads/' + name,
    ]
    for ref in possible_refs:
        if build.get_ref(ref):
            return build.get_ref(ref)

    # Name is a SHA1 hashed object
    is_hex = all (char in string.hexdigits for char in name)
    if len (name) == 40 and is_hex:
        return name

    assert False, f'Unknown name: ' + name
