import random
log_file = open('./AS1239.log')
whole_list = []
j = 0
whole_list = []
for whole_path in log_file:
    whole_path_1 = whole_path.strip('[')
    whole_path_2 = whole_path_1.strip(']\n')
    path_len = len(whole_path_2.split('), '))
    if path_len > 9:
        j+=1
        print j
        paths = whole_path_2.split(', ')
        #print("paths are %s"%paths)
        i = 0
        node_path = []
        while i < 20:
            paths[i] = paths[i].strip('(')
            paths[i] = paths[i].strip(')')
            paths[i+1] = paths[i+1].strip('(')
            paths[i+1] = paths[i+1].strip(')')
            node_path.append(((int(paths[i])),int(paths[i+1])))
            i+=2
        whole_list.append(node_path)
print j
random_index = random.sample(range(j),120)
print random_index
f = open('./selected_path.log','w')
for index in random_index:
    print>>f, whole_list[index]    



