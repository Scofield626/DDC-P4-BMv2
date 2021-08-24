import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FILES = ['send_log.txt', 'recv_log.txt']

if __name__ == '__main__':

    send_list = []
    recv_list = []
    file_handles = {filename: open(filename, 'r') for filename in FILES}
    while 1:
        for filename, fi in file_handles.items():
            line = next(fi, None)
            if line is not None:
                line = line.rstrip('\n')
                if line.split(" ")[1] != 0:
                    if filename == FILES[0]:
                        send_list.append(line.split(" ")[1])
                    else:
                        recv_list.append(line.split(" ")[1])
            else:
                fi.close()
                break
        if line is None:
            break

    data_0 = [] # original 
    data_1 = [] # 2 failures
    data_2 = [] # 10 failures
    result_1 = [] 
    result_2 = []
    print(send_list)
    print(recv_list)

    for i in range(len(send_list)):
        diff = float(send_list[i]) - float(recv_list[i])
        if i % 30 <= 9: data_0.append(diff)
        elif i % 30 <= 19: data_1.append(diff)
        else: data_2.append(diff)
    
    for i in range(len(data_0)):
        if data_0[i] <= 0.05: # erase some abnormal data (normally 3s to 5s) due to record deviations
            result_1.append(0)
            result_2.append(0)
            #continue
        else:
            add_value_1 = (data_1[i]/data_0[i])*100
            if add_value_1 < 0: 
                result_1.append(100)
            else:
                result_1.append(add_value_1)
            add_value_2 = (data_2[i]/data_0[i])*100
            if add_value_2 < 0: 
                result_2.append(100)
            else:
                result_2.append(add_value_2)
    
    print(max(result_1))
    print(max(result_2))
    
    
    #x = np.arange(0, 150)
    result_1.sort()
    result_2.sort()
    #x_2 = np.array(result_2.sort())
    freq_1 = np.array(result_1)
    freq_2 = np.array(result_2)
    pdf_1 = freq_1/np.sum(freq_1)
    pdf_2 = freq_2/np.sum(freq_2)
    cdf_1 = np.cumsum(pdf_1)
    cdf_2 = np.cumsum(pdf_2)
   
    #print freq_1
    #print freq_2
    print cdf_1
    print cdf_2
    
    # only plot percentage increases
    index = 0
    for i in range(len(result_1)):
        if result_1[i]>100:
            index = i
            break

    my_x_ticks = np.arange(100,1800,400)
    my_y_ticks = np.arange(0.8,1.02,0.02)
    ax = plt.subplot()
    ax.scatter(freq_1[index:], cdf_1[index:], marker='o', s=70, label = "Packet Latency (2 failures)")
    ax.scatter(freq_2[index:], cdf_2[index:], marker='D', s=70, label = "Packet Latency (10 failures)")
    plt.ylabel('CDF over packets')
    plt.xlabel('Percentage Increase in Latency')
    plt.xticks(my_x_ticks, [0,400,800,1200,1600], fontsize=22)
    plt.yticks(my_y_ticks, fontsize=22)
    plt.ylim((0.8,1.01))
    plt.xlim((100, 1800))
    plt.grid(linestyle='-.')
    plt.legend(loc="lower right", fontsize=18)
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.savefig("./pktLatency/figure_2.png")

