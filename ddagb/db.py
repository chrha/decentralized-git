from os import error
import rocksdb
import json
import hashlib
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import binascii
def put_db(key, value, address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    db.put(bytes(key), bytes(value), address)

def get_db(key, address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    return db.get(bytes(key), address)


def create_block(file,body,address, ref, pub_key, priv_key):
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
            "commit" : file,
            "branch" : ref,
            "user" : pub_key,
            "dag_parents": dag_parents
        })
        dag_h= SHA256.new(tot.encode())
        dag_hash=dag_h.hexdigest()
        print("about to sign")
        try:
            signature = pkcs1_15.new(priv_key).sign(dag_h)
            signature = binascii.hexlify(signature).decode('ascii')
            print("just signed")
        except:
            print("failed to sign")
        #find new way to generate key, hash rest of block also to generate key, might cause issues with parent hash,
        #since git commit hash will then be different from DAG hash.
        #put_db(dag_hash.encode(),tot.encode(),address.encode())

        return json.dumps({"sig" : signature, "block_hash": dag_hash, "block_data" : tot})
    return



def add_block(block, address):
    block = json.loads(block)
    put_db(block['block_hash'].encode(), block['block_data'].encode(), address.encode())


def get_block(file,body,address, ref,pu_key,pub_key, signature):
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
        #p_key= pub_key.export_key().decode()
        tot=json.dumps({
            "tree": t_data,
            "parents": parent_list,
            "message": msg,
            "commit" : file,
            "branch" : ref,
            "user" : pub_key,
            "dag_parents": dag_parents
        })
        dag_h= SHA256.new(tot.encode())
        dag_hash=dag_h.hexdigest()
        sig= binascii.unhexlify(signature)

        try:
            pkcs1_15.new(pu_key).verify(dag_h, sig)
            print ("The signature is valid.")
            put_db(dag_hash.encode(),tot.encode(),address.encode())
        except (ValueError, TypeError):
            print ("The signature is not valid.")

        #find new way to generate key, hash rest of block also to generate key, might cause issues with parent hash,
        #since git commit hash will then be different from DAG hash.






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


#for e in get_all_values("2422/dag.db"):
#    print(e)
#    print('/n')
