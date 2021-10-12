import build
import os
import itertools
import operator
from collections import deque,namedtuple
from pathlib import Path
import string
import diff

def write_tree ():
    # Index is flat, we need it as a tree of dicts
    index_as_tree = {}
    with build.get_index () as index:
        for path, oid in index.items ():
            path = path.split ('/')
            dirpath, filename = path[:-1], path[-1]

            current = index_as_tree
            # Find the dict for the directory of this file
            for dirname in dirpath:
                current = current.setdefault (dirname, {})
            current[filename] = oid

    def write_tree_recursive (tree_dict):
        entries = []
        for name, value in tree_dict.items ():
            if type (value) is dict:
                type_ = 'tree'
                oid = write_tree_recursive (value)
            else:
                type_ = 'blob'
                oid = value
            entries.append ((name, oid, type_))

        tree = ''.join (f'{type_} {oid} {name}\n'
                        for name, oid, type_
                        in sorted (entries))
        return build.hash_obj (tree.encode (), 'tree')

    return write_tree_recursive (index_as_tree)


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

def get_index_tree ():
    with build.get_index () as index:
        return index

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


def read_tree (tree_oid, update_working=False):
    with build.get_index () as index:
        index.clear ()
        index.update (get_tree (tree_oid))

        if update_working:
            _checkout_index (index)


def read_tree_merged (t_base, t_HEAD, t_other, update_working=False):
    with build.get_index () as index:
        index.clear ()
        index.update (diff.merge_trees (
            get_tree (t_base),
            get_tree (t_HEAD),
            get_tree (t_other)
        ))

        if update_working:
            _checkout_index (index)

def _checkout_index (index):
    empty_working_dir ()
    for path, oid in index.items ():
        os.makedirs (os.path.dirname (f'./{path}'), exist_ok=True)
        with open (path, 'wb') as f:
            f.write (build.get_obj (oid, 'blob'))



def ignore(path):
    return ".dagit" in Path(path).parts


def commit(msg):
    commit= "tree " + write_tree() + "\n"
    head= build.get_ref('HEAD').value
    if head:
        commit += "parent " + head + '\n'
    merge_head = build.get_ref ('MERGE_HEAD').value
    if merge_head:
        commit += f'parent {merge_head}\n'
        build.delete_ref ('MERGE_HEAD', deref=False)
    commit += "\n" + msg + "\n"
    obj = build.hash_obj(commit.encode(),"commit")
    build.update_ref('HEAD',build.RefValue(symbolic=False,value=obj))
    return obj


Commit = namedtuple ('Commit', ['tree', 'parents', 'message'])


def get_commit (goid):
    parents = []
    commit = build.get_obj (goid, 'commit').decode ()
    lines = iter (commit.splitlines ())
    message = ""
    for line in itertools.takewhile (operator.truth, lines):
        try:
            key, value = line.split (' ', 1) #might cause bug
        except:
            message = line
            break
        if key == 'tree':
            tree = value
        elif key == 'parent':
            parents.append (value)
    message = message + '\n'.join (lines)
    return Commit (tree=tree, parents=parents, message=message)

def checkout(name):
    goid=get_goid(name)
    commit = get_commit(goid)
    read_tree (commit.tree, update_working=True)
    if is_branch(name):
        head= build.RefValue(symbolic=True, value="refs/heads/"+name)
    else:
        head=build.RefValue(symbolic=False,value=goid)
    build.update_ref('HEAD',head,deref=False)

def create_tag(name, goid):
    # create the tag later
    tag= "refs/tags/"+name
    build.update_ref(tag,build.RefValue(symbolic=False,value=goid))

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
        if build.get_ref(ref,deref=False).value:
            return build.get_ref(ref).value

    # Name is a SHA1 hashed object
    is_hex = all (char in string.hexdigits for char in name)
    if len (name) == 40 and is_hex:
        return name

    assert False, f'Unknown name: ' + name

def get_working_tree ():
    result = {}
    for root, _, filenames in os.walk ('.'):
        for filename in filenames:
            path = os.path.relpath (f'{root}/{filename}')
            if ignore(path) or not os.path.isfile (path):
                continue
            with open (path, 'rb') as f:
                result[path] = build.hash_obj (f.read ())
    return result


def get_commit_and_parents(goids):
    goids=deque(goids)
    visited= set()

    while goids:
        goid=goids.popleft()
        if not goid or goid in visited:
            continue
        visited.add(goid)
        yield goid

        commit=get_commit(goid)
        # Return first parent next
        goids.extendleft (commit.parents[:1])
        # Return other parents later
        goids.extend (commit.parents[1:])


def iter_objects_in_commits (goids):
    visited = set ()
    def iter_objects_in_tree (goid):
        visited.add (goid)
        yield goid
        for type_, goid, _ in iter_tree (goid):
            if goid not in visited:
                if type_ == 'tree':
                    yield from iter_objects_in_tree (goid)
                else:
                    visited.add (goid)
                    yield goid

    for goid in get_commit_and_parents (goids):
        yield goid
        commit = get_commit (goid)
        if commit.tree not in visited:
            yield from iter_objects_in_tree (commit.tree)


def create_branch(name,goid):
    build.update_ref("refs/heads/"+name, build.RefValue(symbolic=False,value=goid))


def is_branch(name):
    return build.get_ref("refs/heads/" + name).value is not None


def init():
    build.init()
    build.update_ref('HEAD', build.RefValue(symbolic=True,value="refs/heads/master"))


def get_branch_name ():
    head = build.get_ref ('HEAD', deref=False)
    if not head.symbolic:
        return None
    head = head.value
    assert head.startswith ('refs/heads/')
    return os.path.relpath (head, 'refs/heads')

def iter_branch_names ():
    for refname, _ in build.iter_refs ('refs/heads/'):
        yield os.path.relpath (refname, 'refs/heads/')

def reset (oid):
    build.update_ref ('HEAD', build.RefValue (symbolic=False, value=oid))

def merge (other):
    HEAD = build.get_ref ('HEAD').value
    assert HEAD
    merge_base = get_merge_base (other, HEAD)
    c_other = get_commit (other)
        
    # Handle fast-forward merge
    if merge_base == HEAD:
        read_tree (c_other.tree, update_working=True)
        build.update_ref ('HEAD',
                         build.RefValue (symbolic=False, value=other))
        print ('Fast-forward merge, no need to commit')
        return

    build.update_ref ('MERGE_HEAD', build.RefValue (symbolic=False, value=other))
    c_base = get_commit (merge_base)
    c_HEAD = get_commit (HEAD)
    read_tree_merged (c_base.tree, c_HEAD.tree, c_other.tree, update_working=True)
    print ('Merged in working tree\nPlease commit')


def get_merge_base (oid1, oid2):
    parents1 = set (get_commit_and_parents ({oid1}))

    for oid in get_commit_and_parents ({oid2}):
        if oid in parents1:
            return oid


def is_ancestor_of (commit, maybe_ancestor):
    return maybe_ancestor in get_commit_and_parents ({commit})

def add (filenames):
    def add_file (filename):
        # Normalize path
        filename = os.path.relpath (filename)
        with open (filename, 'rb') as f:
            oid = build.hash_obj (f.read ())
        index[filename] = oid

    def add_directory (dirname):
        for root, _, filenames in os.walk (dirname):
            for filename in filenames:
                # Normalize path
                path = os.path.relpath (f'{root}/{filename}')
                if ignore (path) or not os.path.isfile (path):
                    continue
                add_file (path)

    with build.get_index () as index:
        for name in filenames:
            if os.path.isfile (name):
                add_file (name)
            elif os.path.isdir (name):
                add_directory (name)
