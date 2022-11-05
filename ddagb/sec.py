import db
import binascii
from Crypto.Signature import pkcs1_15
import json
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256

def is_valid(message, ledger):
    if not has_parent(message, ledger):
        return False
    else:
        return True

def is_signed(message, key):
    key = RSA.importKey(key)
    for block in message["blocks"]:
        block = json.loads(block)
        dag_h= SHA256.new(block['block_data'].encode())
        dag_hash=dag_h.hexdigest()
        signature = binascii.unhexlify(block['sig'])
        pkcs1_15.new(key).verify(dag_h, signature)
    return True

def has_dag_parents(message, ledger):
     for block in message["blocks"]:
        block = json.loads(block)
        block_data = json.loads(block['block_data'])
        parents = block_data['dag_parents']
        for parent in parents:
            if not db.get_db(parent, ledger):
                return False
        return True



def is_owner(message, key, ledger):
    #for each block (commit) check that they own branch
    #find first instance of ref and check the pub key of that block
    #if public key same as publisher allow appending to database

    #NEED TO MAYBE CHECK THAT REF DOES NOT ALREADY EXIST
    for block in message["blocks"]:
        block = json.loads(block)
        block_data = json.loads(block['block_data'])
        parents = block_data['dag_parents']
        ref = block_data['branch']
        for parent in parents:
            parent_data = json.loads(db.get_db(parent.encode(), ledger))
            parent_ref = parent_data["branch"]
            parent_key = parent_data["user"]
            if ref == "refs/heads/master":
                return True
            if parent_ref == ref:
                if key != parent_key:
                    print("Invalid operation")
                    return False
        return True

def has_parent(commit, address):
    for key in commit:

        value=commit[key].encode()
        type, empty , data = value.partition(b'\x00')
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

            #patch for multiple parents
            dag_parents = db.find_dag_parents(parent_list,address)
            if parent_list == [] or dag_parents != []:
                return True
            else:
                return False
