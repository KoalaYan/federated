import os
import sys
import os.path
import numpy as np
import matplotlib.pyplot as plt

if __name__ == '__main__':
    fileList = os.listdir('./')
    print(fileList)
    # symbol = ['-','--',':','-.']
    colors = ['r','b','y','c','m','g','black']
    plt.figure()
    for id in range(len(fileList)):
        file = fileList[id]
        fileExt = os.path.splitext(file)[-1]
        if fileExt == '.log':
            costAvg = np.zeros(120, dtype=float)
            num = np.zeros(120, dtype=int)
            f = open(file, 'r')
            context = f.readlines()
            for line in context:
                parts = line.split(',')
                epoch = int(parts[1].split(':')[1])
                cost = float(parts[2].split('=')[1])
                costAvg[epoch-1] += cost
                num[epoch-1] += 1
                # (epoch, cost)
            for index in range(costAvg.size):
                costAvg[index] /= num[index]
                # print(costAvg[index])
            x = np.arange(120)

            # 1.线图
            #调用plt。plot来画图,横轴纵轴两个参数即可
            # plt.plot(x[19:],costAvg[19:])
            plt.plot(x[19:],costAvg[19:], color=colors[id], label=file)
            plt.xlabel(u'Epoch')#fill the meaning of X axis
            plt.ylabel(u'AvgCost')#fill the meaning of Y axis
    plt.legend()
    plt.title('Comparison')#add the title of the figure
    plt.show()
    # f = open('', 'r')