import rocksdb
import json

def put_db(key, value, address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    db.put(bytes(key), bytes(value), address)

def get_db(key, address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    return db.get(bytes(key), address)

def append_commit(file,body,address):
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

        tot=json.dumps({
            "tree": t_data,
            "parents": parent_list,
            "message": msg
        })
        put_db(file.encode(),tot.encode(),address.encode())

def get_all_keys(address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    it = db.iterkeys()
    it.seek_to_first()
    return list(it)


def get_all_values(address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    it = db.itervalues()
    it.seek_to_first()
    return list(it)

#print(get_all_values("remote/dag.db"))

