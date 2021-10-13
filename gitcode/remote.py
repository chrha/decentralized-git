import os
import build
import structure

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

    # Push missing objects
    for oid in objects_to_push:
        build.push_object (oid, remote_path)

    # Update server ref to our value
    
    build.send_ref_remote(refname)