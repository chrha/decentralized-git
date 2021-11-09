import os
import build
import structure
import itertools
import functools

REMOTE_REFS_BASE = 'refs/heads/'
LOCAL_REFS_BASE = 'refs/remote/'


def fetch (remote_path):
    # Get refs from server
    refs = _get_remote_refs (remote_path, REMOTE_REFS_BASE)
    # Fetch missing objects by iterating and fetching on demand
    
    for oid in structure.iter_objects_in_commits (refs.values ()):
        build.fetch_object_if_missing (oid, remote_path)

    # Update local refs to match server
    for remote_name, value in refs.items ():
        refname = os.path.relpath (remote_name, REMOTE_REFS_BASE)
        build.update_ref (f'{LOCAL_REFS_BASE}/{refname}',
                         build.RefValue (symbolic=False, value=value))


def _get_remote_refs (remote_path, prefix=''):
    with build.change_git_dir (remote_path):
        return {refname: ref.value for refname, ref in build.iter_refs (prefix)}

def push (remote_path, refname):
    # Get refs data
    remote_refs = _get_remote_refs (remote_path)
    remote_ref = remote_refs.get (refname)
    local_ref = build.get_ref (refname).value
    assert local_ref
    
    # Don't allow force push
    assert not remote_ref or structure.is_ancestor_of (local_ref, remote_ref)

    known_remote_refs = filter (build.object_exists, remote_refs.values ())
    remote_objects = set (structure.iter_objects_in_commits (known_remote_refs))
    local_objects = set (structure.iter_objects_in_commits ({local_ref}))
    objects_to_push = local_objects - remote_objects

    #TODO: sort commits

    objects_to_push = sort_commits(objects_to_push)
    #objects_to_push.reverse()
    # Push missing objects
    for oid in objects_to_push:
        build.push_object (oid, remote_path)


    build.send_commit(objects_to_push, refname)
    # Update server ref to our value

def sort_commits(list_obj):
    #implementation does not consider multiple parents
    commit_list =  [c for c in list_obj if build.isType(c,'commit')]
    blob_tree_obj = [o for o in list_obj if not o in commit_list]
    cp_list = [(c,structure.get_commit(c).parents) for c in commit_list]
    sort_list = [x[0] for x in cp_list if not (x[1] and (x[1][0] in commit_list))]
    cp_list.remove((sort_list[0],[]))

    for c1 in sort_list:
        for c2, p2 in cp_list:
            if p2[0] == c1:
                sort_list.append(c2)
                cp_list.remove((c2,p2))
    return sort_list + blob_tree_obj
