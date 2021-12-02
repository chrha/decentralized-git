from os import error
import rocksdb
import json
import hashlib
def put_db(key, value, address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    db.put(bytes(key), bytes(value), address)

def get_db(key, address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    return db.get(bytes(key), address)

def append_commit(file,body,address, ref, id):
    body=body.encode()
    type, empty , data = body.partition(b'\x00')
    data=data.decode()
    data_list=data.split("\n")
    type=type.decode()
    if type== "commit":
        t_data= data_list[0].split(" ",1)[1]
        parent_list=[]
        i = 1
        while(i < 3):
            try:
                parent, p_data= data_list[i].split(" ",1)
            except:
                break
            if "parent" in parent:
                parent_list.append(p_data)
            else:
                break
            i+=1

        msg = ''.join(data_list[i:])
        dag_parents= find_dag_parents(parent_list, address)
        tot=json.dumps({
            "tree": t_data,
            "parents": parent_list,
            "message": msg,
            "user" : id,
            "branch" : ref,
            "commit" : file,
            "dag_parents": dag_parents
        })
        dag_hash= hashlib.sha256(tot.encode()).hexdigest()
        #find new way to generate key, hash rest of block also to generate key, might cause issues with parent hash,
        #since git commit hash will then be different from DAG hash.
        put_db(dag_hash.encode(),tot.encode(),address.encode())


def find_dag_parents(parent_list, address):
    #for elem in parent_list:
    dag_parents=[]
    blocks = get_all_items(address)

    for key,block in blocks:
        block=json.loads(block)
        if block["commit"] in parent_list:
            dag_parents.append(key)
        if len(dag_parents)==len(parent_list):
            #print(dag_parents)
            return dag_parents
    #print(dag_parents)
    return dag_parents


def get_all_items(address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    it = db.iteritems()
    it.seek_to_first()
    return [(k[0].decode(),k[1].decode()) for k in list(it)]


def get_all_keys(address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    it = db.iterkeys()
    it.seek_to_first()
    return [k.decode() for k in list(it)]


def get_all_values(address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    it = db.itervalues()
    it.seek_to_first()
    return list(it)


#for e in get_all_values("1910/dag.db"):
    #print(e)
    #print('/n')
