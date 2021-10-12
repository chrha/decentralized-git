import rocksdb

def put_db(key, value, address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    db.put(bytes(key), bytes(value), address)

def get_db(key, address):
    db = rocksdb.DB(address, rocksdb.Options(create_if_missing=True))
    return db.get(bytes(key), address)

def append_commit(file,body):
    body=body.encode()
    type, empty , data = body.partition(b'\x00')
    data=data.decode()
    #data=data.split("\n")
    type=type.decode()
    if type== "commit":
        t_data= data.getline().split(" ",1)[1]
        parent_list=[]

        while True:
            tmp=data.getline()
            if "parent" in tmp:
                parent, p_data= data.getline().split(" ",1)
                parent_list.append(p_data)
            else:
                break



        msg= tmp

        tot=json.dumps({
            "tree": t_data,
            "parents": parent_list,
            "message": msg
        })
        put_db(file.encode(),tot.encode(),"remote/dag.db".encode())
