
import argparse
import build
import os
import sys
import structure
import pathlib
import textwrap
import subprocess
import diff
import remote

def parse():
    parser= argparse.ArgumentParser()
    # Add subcommands for git, i.e init, commit etc
    sub_parser= parser.add_subparsers(dest="git command")
    sub_parser.required=True
    #add init command parser
    init_parser= sub_parser.add_parser("init")
    init_parser.set_defaults(func=init)

    #add object hash as command, with a file as argument
    hashobj_parser= sub_parser.add_parser("hash-object")
    hashobj_parser.set_defaults(func=hash_object)
    hashobj_parser.add_argument("file")

    #add cat of an object hash as command, with hash object as argument
    cat_parser= sub_parser.add_parser("cat-file")
    cat_parser.set_defaults(func=cat_file)
    cat_parser.add_argument("object",type=structure.get_goid)

    #add command for creating hash objects for trees
    wtree_parser= sub_parser.add_parser("write-tree")
    wtree_parser.set_defaults(func=write_tree)
    #add command for retrieving tree into directory from hash object
    rtree_parser= sub_parser.add_parser("read-tree")
    rtree_parser.set_defaults(func=read_tree)
    rtree_parser.add_argument("tree",type=structure.get_goid)

    commit_parser= sub_parser.add_parser("commit")
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('-m', '--message', required=True)

    log_parser= sub_parser.add_parser("log")
    log_parser.set_defaults(func=log)
    log_parser.add_argument ('goid',default='@',type=structure.get_goid, nargs='?')

    checkout_parser= sub_parser.add_parser("checkout")
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument("commit")

    tag_parser = sub_parser.add_parser ('tag')
    tag_parser.set_defaults (func=tag)
    tag_parser.add_argument ('name')
    tag_parser.add_argument ('goid',default='@',type=structure.get_goid ,nargs='?')

    reset_parser = sub_parser.add_parser ('reset')
    reset_parser.set_defaults (func=reset)
    reset_parser.add_argument ('commit', type=structure.get_goid)

    show_parser = sub_parser.add_parser ('show')
    show_parser.set_defaults (func=show)
    show_parser.add_argument ('oid', default='@', type=structure.get_goid, nargs='?')

    diff_parser = sub_parser.add_parser ('diff')
    diff_parser.set_defaults (func=_diff)
    diff_parser.add_argument ('--cached', action='store_true')
    diff_parser.add_argument ('commit', nargs='?')

    merge_parser = sub_parser.add_parser ('merge')
    merge_parser.set_defaults (func=merge)
    merge_parser.add_argument ('commit', type=structure.get_goid)

    merge_base_parser = sub_parser.add_parser ('merge-base')
    merge_base_parser.set_defaults (func=merge_base)
    merge_base_parser.add_argument ('commit1', type=structure.get_goid)
    merge_base_parser.add_argument ('commit2', type=structure.get_goid)

    add_parser = sub_parser.add_parser ('add')
    add_parser.set_defaults (func=add)
    add_parser.add_argument ('files', nargs='+')
    
    fetch_parser = sub_parser.add_parser ('fetch')
    fetch_parser.set_defaults (func=fetch)
    fetch_parser.add_argument ('remote')

    push_parser = sub_parser.add_parser ('push')
    push_parser.set_defaults (func=push)
    push_parser.add_argument ('remote')
    push_parser.add_argument ('branch')



    k_parser = sub_parser.add_parser ('k')
    k_parser.set_defaults (func=k)


    branch_parser = sub_parser.add_parser ('branch')
    branch_parser.set_defaults (func=branch)
    branch_parser.add_argument ('name',nargs='?')
    branch_parser.add_argument ('start_point',default='@',type=structure.get_goid ,nargs='?')

    status_parser = sub_parser.add_parser ('status')
    status_parser.set_defaults (func=status)


    return parser.parse_args()


def init(args):
    structure.init()
    print('initialized an empty dagit directory at' + os.path.join(os.getcwd(),build.GIT_DIR) )

def hash_object(args):
    with open (args.file,"rb") as f:
        print(build.hash_obj(f.read()))

def cat_file(args):
    sys.stdout.flush()
    sys.stdout.buffer.write(build.get_obj(args.object, expected=None))

def write_tree(args):
    print(structure.write_tree())

def read_tree(args):
    structure.read_tree(args.tree)

def commit(args):
    print(structure.commit(args.message))

def reset (args):
    structure.reset (args.commit)

def _diff (args):
    tree = args.commit and structure.get_commit (args.commit).tree

    result = diff.diff_trees (structure.get_tree (tree), structure.get_working_tree ())
    sys.stdout.flush ()
    sys.stdout.buffer.write (result)

def log (args):

    #goid = args.goid or build.get_ref('HEAD')
    #goid=args.goid
    #while goid:
    refs = {}
    for refname, ref in build.iter_refs ():
        refs.setdefault (ref.value, []).append (refname)


    for goid in structure.get_commit_and_parents({args.goid}):
        commit = structure.get_commit (goid)

        #print ("commit "+ goid + '\n')
        _print_commit (goid, commit, refs.get (goid))

        goid = commit.parents


def _print_commit (oid, commit, refs=None):
    refs_str = f' ({", ".join (refs)})' if refs else ''
    print (f'commit {oid}{refs_str}\n')
    print (textwrap.indent (commit.message, '    '))
    print ('')

def show (args):
    if not args.oid:
        return
    commit = structure.get_commit (args.oid)
    parent_tree = None
    if commit.parents:
        parent_tree = structure.get_commit (commit.parents[0]).tree
    _print_commit (args.oid, commit)
    result = diff.diff_trees (structure.get_tree (parent_tree), structure.get_tree (commit.tree))
    sys.stdout.flush()
    sys.stdout.buffer.write(result)


def checkout(args):
    structure.checkout(args.commit)

def tag(args):
    #goid = args.goid or build.get_ref('HEAD')
    structure.create_tag(args.name, args.goid)

def k(args):
    dot = 'digraph commits {\n'
    goids=set()
    for ref, name in build.iter_refs(deref=False):
        dot += f'"{ref}" [shape=note]\n'
        dot += f'"{ref}" -> "{name.value}"\n'
        if not name.symbolic:
            goids.add(name.value)
    for goid in structure.get_commit_and_parents(goids):
        commit= structure.get_commit(goid)
        dot += f'"{goid}" [shape=box style=filled label="{goid[:10]}"]\n'
        for parent in commit.parents:
            dot += f'"{goid}" -> "{parent}"\n'

    dot += '}'
    print (dot)

    with subprocess.Popen (
            ['dot', '-Tx11', '/dev/stdin'],
            stdin=subprocess.PIPE) as proc:
        proc.communicate (dot.encode ())

def branch(args):

    if not args.name:
        current = structure.get_branch_name ()
        for branch in structure.iter_branch_names ():
            prefix = '*' if branch == current else ' '
            print (f'{prefix} {branch}')
    else:
        structure.create_branch (args.name, args.start_point)
        print (f'Branch {args.name} created at {args.start_point[:10]}')

def status (args):
    HEAD = structure.get_goid ('@')
    branch = structure.get_branch_name ()
    if branch:
        print (f'On branch {branch}')
    else:
        print (f'HEAD detached at {HEAD[:10]}')
    
    merge_head = build.get_ref ('MERGE_HEAD').value
    if merge_head:
        print (f'Merging with {merge_head[:10]}')

    print ('\nChanges to be committed:\n')
    HEAD_tree = HEAD and structure.get_commit (HEAD).tree
    for path, action in diff.iter_changed_files (structure.get_tree (HEAD_tree),
                                                 structure.get_index_tree ()):
        print (f'{action:>12}: {path}')

    print ('\nChanges not staged for commit:\n')
    for path, action in diff.iter_changed_files (structure.get_index_tree (),
                                                 structure.get_working_tree ()):
        print (f'{action:>12}: {path}')

def merge (args):
    structure.merge (args.commit)

def merge_base (args):
    print (structure.get_merge_base (args.commit1, args.commit2))

def fetch (args):
    remote.fetch (args.remote)


def push (args):
    remote.push (args.remote, f'refs/heads/{args.branch}')

def add (args):
    structure.add (args.files)


def main():
    with build.change_git_dir ('.'):
        args = parse ()
        args.func (args)

main()
