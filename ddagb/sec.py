import db

def is_valid(commit, ledger):
    if not has_parent(commit, ledger):
        return False
    else:
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

#if "ref" in msg:
        #ref = msg['ref']
        #r= SHA256.new(ref.encode())
        #signature = pkcs1_15.new(pr_key).sign(r)
        #bla=binascii.hexlify(signature).decode('ascii')
        #bla2=binascii.unhexlify(bla)
        #try:
            #pkcs1_15.new(pu_key).verify(r,bla2)
            #print("correct verification")
        #except:
            #print("unsuccessful verify")