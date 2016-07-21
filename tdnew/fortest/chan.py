# -*- coding: utf-8 -*-
__author__ = 'xujh'

import matplotlib.pyplot as plt
import os
import pandas as pd
import datetime
import matplotlib.dates as dt
from matplotlib.lines import Line2D
from matplotlib.dates import *
import math
import nanotime
import numba

from pylab import *

MIN_FLOAT = 1e-4

mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['figure.subplot.top'] = 0.96
mpl.rcParams['figure.subplot.bottom'] = 0.03
mpl.rcParams['figure.subplot.left'] = 0.03
mpl.rcParams['figure.subplot.right'] = 0.98
st = nanotime.now()
hqdatadir = 'D:\TdxW_HuaTai\T0002\export2'
code = '999999'
# code = '399006'
filepath = os.path.join(hqdatadir, (code + '.txt'))
# if not os.path.exists(filepath):
#     logger.critical("filepath %s does not exist", filepath)
#     raise RuntimeError, 'filepath does not exist'

rnames = ['d', 't', 'open', 'high', 'low', 'close', 'volume', 'amt']
df5mKline = pd.read_table(filepath,
                          engine='python', sep=',',
                          encoding='gbk',
                          names=rnames,
                          parse_dates={'time': ['d', 't']},
                          index_col='time',
                          skiprows=2,
                          skipfooter=1)
print ('load txt data cost:%d' % (nanotime.now() - st).milliseconds())


class Base(object):
    def __init__(self):
        self.idx = 0

    def __str__(self):
        return str(self.__dict__) + '\n'

    def __repr__(self):
        return str(self)


class Kline(Base):
    def __init__(self, **kwargs):
        super(Kline, self).__init__()
        # shape 用于区分是顶分型还是底分型
        self.high = kwargs['high']
        self.low = kwargs['low']
        self.shape = kwargs['shape'] if 'shape' in kwargs else 'un'
        self.time = kwargs['time']


class PenPoint(Base):
    def __init__(self, **kwargs):
        super(PenPoint, self).__init__()
        # kidx在标准k线列表中所处的index，value顶点或者底点的值，shape顶分型还是底分型
        self.kidx = kwargs['kidx']
        self.value = kwargs['value']
        self.shape = kwargs['shape'] if 'shape' in kwargs else 'un'
        self.stable = 0


class LinePoint(Base):
    def __init__(self, **kwargs):
        super(LinePoint, self).__init__()
        # kidx在标准k线列表中所处的index，pidx在笔列表中所处的index,value顶点或者底点的值，shape顶分型还是底分型
        #pidx在笔列表中所处的index
        self.pidx = kwargs['pidx']



class Seq(Base):
    def __init__(self, **kwargs):
        super(Seq, self).__init__()
        self.bpidx = kwargs['bpidx']
        self.epidx = kwargs['epidx']
        self.bvalue = kwargs['bvalue']
        self.evalue = kwargs['evalue']
        self.high = kwargs['high'] if 'high' in kwargs else 'un'
        self.low = kwargs['low'] if 'low' in kwargs else 'un'
        self.shape = kwargs['shape'] if 'shape' in kwargs else 'un'


class Toolkit(object):
    _shapeVariableSet = ['na', 'u', 'd']
    _shapeUpDown = ['u', 'd']
    def __init__(self):
        pass

    # 是否存在包含关系
    @staticmethod
    def isContain(prekline, curkline):
        # 向左包含 n+1包含n
        if curkline.high >= prekline.high and curkline.low <= prekline.low:
            return True
        # 向右包含 n包含n+1
        elif curkline.high <= prekline.high and curkline.low >= prekline.low:
            return True
        else:
            return False


    # 判断是上升趋势还是下降趋势,True为上升趋势，False为下降趋势
    @staticmethod
    def isUp(line1, line2):
        if line2.high >= line1.high and line2.low >= line1.low:
            return True
        else:
            return False


    @staticmethod
    def getShape(line1, line2, line3):
        # 顶分型
        if line2.high > line1.high \
                and line2.high > line3.high:
            return 'u'
        # 底分型
        elif line2.low < line1.low \
                and line2.low < line3.low:
            return 'd'
        # 未知情况
        else:
            return 'na'

        # # 顶分型
        # if line2.high > line1.high \
        #         and line2.high > line3.high \
        #         and line2.low > line1.low \
        #         and line2.low > line3.low:
        #     return 'u'
        # # 底分型
        # elif line2.high < line1.high \
        #         and line2.high < line3.high \
        #         and line2.low < line1.low \
        #         and line2.low < line3.low:
        #     return 'd'
        # # 未知情况
        # else:
        #     return 'na'


    @staticmethod
    # @profile
    def append(list, dict_value):
        dict_value.idx = len(list)
        list.append(dict_value)

    @staticmethod
    # @profile
    def procContain(list, isUp, newkline):
        if len(list) < 1 or not Toolkit.isContain(list[-1], newkline):
            Toolkit.append(list, newkline)
        else:
            # 高点取高值，低点也取高值，简单的说就是“上升取高高”
            if isUp:
                newkline.high = max(list[-1].high, newkline.high)
                newkline.low = max(list[-1].low, newkline.low)
            # 高点取低值，低点也取低值，简单的说就是“下降取低低”
            else:
                newkline.high = min(list[-1].high, newkline.high)
                newkline.low = min(list[-1].low, newkline.low)
            # 处理完包含关系后，将前一个删除，只保留最终处理完的结果
            list.pop()
            # 递归处理包含关系，有可能出现处理包含之后的元素和之前的元素还存在包含关系
            return Toolkit.procContain(list, isUp, newkline)

    @staticmethod
    # @profile
    def procSeqContain(list, isUp, newseq, needproc = True):
        if not needproc or len(list) < 1 or not Toolkit.isContain(list[-1], newseq):
            Toolkit.append(list, newseq)
        else:
            # 高点取高值，低点也取高值，简单的说就是“上升取高高”
            if isUp:
                if list[-1].high - newseq.high > MIN_FLOAT:
                    newseq.bvalue = newseq.high = list[-1].high
                    newseq.bpidx = list[-1].bpidx
                else:
                    newseq.evalue = newseq.low = list[-1].low
                    newseq.epidx = list[-1].epidx
                # newseq.high = max(list[-1].high, newseq.high)
                # newseq.low = max(list[-1].low, newseq.low)
            # 高点取低值，低点也取低值，简单的说就是“下降取低低”
            else:
                if list[-1].high - newseq.high > MIN_FLOAT:
                    newseq.bvalue = newseq.low = list[-1].low
                    newseq.bpidx = list[-1].bpidx
                else:
                    newseq.evalue = newseq.high = list[-1].high
                    newseq.epidx = list[-1].epidx
                # newseq.high = min(list[-1].high, newseq.high)
                # newseq.low = min(list[-1].low, newseq.low)
            # 处理完包含关系后，将前一个删除，只保留最终处理完的结果
            list.pop()
            # 递归处理包含关系，有可能出现处理包含之后的元素和之前的元素还存在包含关系
            return Toolkit.procSeqContain(list, isUp, newseq, needproc)

    @staticmethod
    def procShape(list):
        has_new_shape = False
        if len(list) < 3:
            return has_new_shape
        for i in xrange(2, len(list)):
            # 性能优化，只做一次推断，不重复推断
            if list[-i].shape in Toolkit._shapeVariableSet:
                break

            _shape = Toolkit.getShape(
                list[-i - 1],
                list[-i],
                list[-i + 1])
            list[-i].shape = _shape
            if _shape in Toolkit._shapeUpDown:
                has_new_shape = True

        return has_new_shape
    # 方向（属于向上笔还是向下笔）
    @staticmethod
    def getDirect(pen_start, pen_end):
        # 向上笔
        if pen_start['value'] < pen_end['value']:
            return 'u'
        # 向下笔
        elif pen_start['value'] > pen_end['value']:
            return 'd'
        # 位置情况
        return 'na'


    @staticmethod
    def lineBreakByPen(seqlist, lineBeginShape, newsq):
        if len(seqlist) < 2:
            return False
        for i in xrange(2, len(seqlist) + 1):
            if (lineBeginShape == 'd' and newsq.low < seqlist[-i].high) \
                or (lineBeginShape == 'u' and newsq.high > seqlist[-i].low):
                return True
        return False

    # 获取subDf中形态为顶分型的最高点
    @staticmethod
    # @profile
    def getUpHighPoint(subList):
        upSubList = [x for x in subList if x.shape == 'u']
        return max(upSubList, key=lambda x: x.high) if upSubList else None


    # 获取subDf中形态为底分型的最低点
    @staticmethod
    # @profile
    def getDownLowPoint(subList):
        downSubList = [x for x in subList if x.shape == 'd']
        return min(downSubList, key=lambda x: x.low) if downSubList else None

    @staticmethod
    def updatePen(penList, idxFrom, kidx, value):
        lastLoc = penList[idxFrom - 1].kidx if len(penList) > abs(idxFrom) else -4
        if kidx - lastLoc >= 4:
            penList[idxFrom].kidx = kidx
            penList[idxFrom].value = value
        else:
            print 'updatePen error'

    @staticmethod
    def checkBeginPoint(penlist, idxFrom):
        if penlist[idxFrom].shape == 'd' and penlist[idxFrom + 3].value > penlist[idxFrom + 1].value:
            return True
        elif penlist[idxFrom].shape == 'u' and penlist[idxFrom + 3].value < penlist[idxFrom + 1].value:
            return True
        else:
            return False


class Chan(object):
    def __init__(self, isUp):
        self._isUp = isUp

        #处理包含关系后的标准k线list
        self._KlineList = []

        #笔的端点list
        self._PenPointList = []

        #第一特征序列
        self._FirstSeqList = []

        #第二特征序列
        self._SecondSeqList = []

        self._bCheckSecondSeqListFlag = False

        # 线段
        self._LinePointList = []

        #self._shapeVariableSet = ['na', 'u', 'd']
        self._shapeUpDown = ['u','d']

        self._print = False

    # @profile
    def procKlineContain(self, list, newkline):
        if len(list) < 2:
            Toolkit.procContain(list, self._isUp, newkline)
        else:
            Toolkit.procContain(list, Toolkit.isUp(list[-2], list[-1]), newkline)

    #@profile
    def onNewKline(self, newkline_):
        newkline = Kline(high = newkline_.high, low = newkline_.low, time=newkline_.name)
        self.procKlineContain(self._KlineList, newkline)
        if Toolkit.procShape(self._KlineList):
            if self.procPen2():
                self.procLine()

    def getUp(self):
        if len(self._LinePointList) > 0:
            return True if self._PenPointList[self._LinePointList[-1].pidx].shape == 'd' else False
        return True

    #判断第一特征序列的第一和第二元素是否存在缺口
    def hasGap(self):
        if self._FirstSeqList[-2].shape == 'u'and self._FirstSeqList[-2].low > self._FirstSeqList[-3].high:
            return True
        elif self._FirstSeqList[-2].shape == 'd' and self._FirstSeqList[-2].high < self._FirstSeqList[-3].low:
            return True
        else:
            return False

    #添加新的线段端点
    def addNewLinePoint(self):
        Toolkit.append(self._LinePointList, LinePoint(pidx=self._FirstSeqList[-2].bpidx))
        self._curFirstSeqBeginPenPoint = self._FirstSeqList[-2].bpidx
        self._FirstSeqList = []

        if len(self._LinePointList) > 1:
            print '_LinePointList', self._LinePointList
        print '--------------------------'

    def addFirstSeq(self):
        while (self._curFirstSeqBeginPenPoint <= len(self._PenPointList) - 5):
            newsq = Seq(bpidx=self._PenPointList[self._curFirstSeqBeginPenPoint + 1].idx,
                        bvalue=self._PenPointList[self._curFirstSeqBeginPenPoint + 1].value,
                        epidx=self._PenPointList[self._curFirstSeqBeginPenPoint + 2].idx,
                        evalue=self._PenPointList[self._curFirstSeqBeginPenPoint + 2].value,
                        high=max(self._PenPointList[self._curFirstSeqBeginPenPoint + 1].value,
                                 self._PenPointList[self._curFirstSeqBeginPenPoint + 2].value),
                        low=min(self._PenPointList[self._curFirstSeqBeginPenPoint + 1].value,
                                self._PenPointList[self._curFirstSeqBeginPenPoint + 2].value))

            Toolkit.procSeqContain(self._FirstSeqList,
                                   self.getUp(), newsq,
                                   not Toolkit.lineBreakByPen(self._FirstSeqList,
                                                          self._PenPointList[self._LinePointList[-1].pidx].shape,
                                                          newsq))

            self._curFirstSeqBeginPenPoint += 2
            if Toolkit.procShape(self._FirstSeqList):
                if len(self._FirstSeqList) > 1:
                    print '_FirstSeqList', self._FirstSeqList

                _shape = 'd' if self._PenPointList[self._LinePointList[-1].pidx].shape == 'u' else 'u'
                if self._FirstSeqList[-2].shape == _shape:
                    # 第一种情况（第一第二元素没有缺口）
                    if not self.hasGap():
                        self.addNewLinePoint()
                        break
                    # 第二种情况（第一第二元素有缺口）,判断第二特征序列是否存在分型
                    else:
                        self._bCheckSecondSeqListFlag = True
                        self._curSecondSeqBeginPenPoint = self._FirstSeqList[-2].bpidx

    def addSecondSeq(self):
        while (self._curSecondSeqBeginPenPoint <= len(self._PenPointList) - 5):
            newsq = Seq(bpidx=self._PenPointList[self._curSecondSeqBeginPenPoint + 1].idx,
                        bvalue=self._PenPointList[self._curSecondSeqBeginPenPoint + 1].value,
                        epidx=self._PenPointList[self._curSecondSeqBeginPenPoint + 2].idx,
                        evalue=self._PenPointList[self._curSecondSeqBeginPenPoint + 2].value,
                        high=max(self._PenPointList[self._curSecondSeqBeginPenPoint + 1].value,
                                 self._PenPointList[self._curSecondSeqBeginPenPoint + 2].value),
                        low=min(self._PenPointList[self._curSecondSeqBeginPenPoint + 1].value,
                                self._PenPointList[self._curSecondSeqBeginPenPoint + 2].value))
            Toolkit.procSeqContain(self._SecondSeqList, not self.getUp(), newsq)

            self._curSecondSeqBeginPenPoint += 2
            if Toolkit.procShape(self._SecondSeqList):
                if len(self._SecondSeqList) > 1:
                    print '_SecondSeqList', self._SecondSeqList
                #第二特征序列出现跟前一线段端点一样的分型，说明第二种情况下的条件成立，线段形成
                #前一线段的分型如果是底分型，则当前线段应该是一个上涨线段，那么第二特征序列应该找一个底分型(原文中没有说明没有找到对应分型时的处理)
                #shape = 'd' if self._PenPointList[self._LinePointList[-1].pidx].shape == 'u' else 'u'
                if self._SecondSeqList[-2].shape == self._PenPointList[self._LinePointList[-1].pidx].shape:
                    self.addNewLinePoint()
                    # self._bCheckSecondSeqListFlag = False
                    # self._SecondSeqList = []
                    # break
                #如果第二种情况不成立，也就是想要形成底分型的，却找到了顶分型，说明线段还没有结束，继续往后寻找
                self._bCheckSecondSeqListFlag = False
                self._SecondSeqList = []
                break


    def procLine(self):
        # 生成笔的最后的两点是会变的，所以只关注笔的最后两点之前的
        # 笔的方向可以通过终点的类型来判断，如果是'u'则是向上笔，如果是'd'则是向下笔
        # 首次开始
        # 笔的数量小于3时，即笔的端点小于4时，算上最后两点是不确定的，所以这里应该是5，不可能形成线段
        if len(self._PenPointList) < 5:
            return

        if len(self._LinePointList) < 1:
            self._curFirstSeqBeginPenPoint = 0 if Toolkit.checkBeginPoint(self._PenPointList, 0) else 1
            Toolkit.append(self._LinePointList, LinePoint(pidx=self._curFirstSeqBeginPenPoint))

        if not self._bCheckSecondSeqListFlag:
            self.addFirstSeq()
        else:
            self.addSecondSeq()


    #获取笔所在端点的值，用于判断是否与之前设定的值一致，否则进行修改
    def getPenPoint(self, penIdxFrom):
        fun = Toolkit.getUpHighPoint if self._PenPointList[penIdxFrom].shape == 'u' else Toolkit.getDownLowPoint
        return fun(self._KlineList[self._PenPointList[penIdxFrom].kidx:])

    #获取笔所在端点的下一个值，主要用于笔新端点的添加
    def getPenPointNext(self, penIdxFrom):
        fun = Toolkit.getUpHighPoint if self._PenPointList[penIdxFrom].shape == 'd' else Toolkit.getDownLowPoint
        return fun(self._KlineList[self._PenPointList[penIdxFrom].kidx:])

    def checkPenFrom(self, penIdxFrom):
        #如果该端点已经被确认过，则不需再进行修正
        if self._PenPointList[penIdxFrom].stable:
            return False

        kline = self.getPenPoint(penIdxFrom)
        if kline is None:
            return False

        if kline.idx > self._PenPointList[penIdxFrom].kidx:
            Toolkit.updatePen(self._PenPointList,
                              penIdxFrom,
                              kline.idx,
                              kline.high if self._PenPointList[penIdxFrom].shape == 'u' else kline.low)
            return True

    def addPenPoint(self):
        while 1:
            kline = self.getPenPointNext(-1)
            if kline is None:
                break
            elif kline.idx - self._PenPointList[-1].kidx < 4:
                break
            else:
                Toolkit.append(self._PenPointList,
                               PenPoint(kidx=kline.idx,
                                        shape=kline.shape,
                                        value= kline.high if kline.shape == 'u' else kline.low))
                if len(self._PenPointList) >= 3:
                    self._PenPointList[-3].stable = 1


    def rebuildPen(self, penIdxFrom):
        for idxF in range(penIdxFrom, 0):
            if self.checkPenFrom(idxF):
                for pcount in range(1, abs(idxF)):
                    self._PenPointList.pop()
                break

        self.addPenPoint()

    #从idxFrom开始检查是否需要修改点的位置，返回需要修改的点的位置，然后删除后续的点
    def checkPenPoint(self, penIdxFrom):
        fun = Toolkit.getUpHighPoint if self._PenPointList[penIdxFrom].shape == 'u' else Toolkit.getDownLowPoint
        kline = fun(self._KlineList[self._PenPointList[penIdxFrom].kidx:])
        if kline is None:
            return
        
        if kline.idx > self._PenPointList[penIdxFrom].kidx:
            return penIdxFrom, kline.idx

    # @profile
    # 返回值为True：有新笔生成，False：没有新笔生成
    def procPen(self):
        # 首次开始
        if len(self._PenPointList) < 2:
            dh = Toolkit.getUpHighPoint(self._KlineList)
            if dh is None:
                return False
            dl = Toolkit.getDownLowPoint(self._KlineList)
            if dl is None:
                return False

            if abs(dh.idx - dl.idx) >= 4:
                if dh.idx > dl.idx:
                    Toolkit.append(self._PenPointList, PenPoint(kidx=dl.idx, shape=dl.shape, value=dl.low))
                    Toolkit.append(self._PenPointList, PenPoint(kidx=dh.idx, shape=dh.shape, value=dh.high))
                else:
                    Toolkit.append(self._PenPointList, PenPoint(kidx=dh.idx, shape=dh.shape, value=dh.high))
                    Toolkit.append(self._PenPointList, PenPoint(kidx=dl.idx, shape=dl.shape, value=dl.low))
                return True
            else:
                return False
        else:
            self.rebuildPen(-1)

    #@profile
    # 返回值为True：有新笔生成，False：没有新笔生成
    def procPen2(self):
        # 首次开始
        if len(self._PenPointList) < 2:
            dh = Toolkit.getUpHighPoint(self._KlineList)
            if dh is None:
                return False
            dl = Toolkit.getDownLowPoint(self._KlineList)
            if dl is None:
                return False

            if abs(dh.idx - dl.idx) >= 4:
                if dh.idx > dl.idx:
                    Toolkit.append(self._PenPointList, PenPoint(kidx=dl.idx, shape=dl.shape, value=dl.low))
                    Toolkit.append(self._PenPointList, PenPoint(kidx=dh.idx, shape=dh.shape, value=dh.high))
                else:
                    Toolkit.append(self._PenPointList, PenPoint(kidx=dh.idx, shape=dh.shape, value=dh.high))
                    Toolkit.append(self._PenPointList, PenPoint(kidx=dl.idx, shape=dl.shape, value=dl.low))
                return True
        else:
            #先看当前高点或者地点是否有更新
            kline = self.getPenPoint(-1)
            if kline.idx > self._PenPointList[-1].kidx:
                Toolkit.updatePen(self._PenPointList,
                                  -1,
                                  kline.idx,
                                  kline.high if self._PenPointList[-1].shape == 'u' else kline.low)
                return True

            kline = self.getPenPointNext(-1)
            if kline is None:
                return False
            elif kline.idx - self._PenPointList[-1].kidx < 4:
                if (self._PenPointList[-2].shape == 'u' and kline.high > self._PenPointList[-2].value) or \
                    (self._PenPointList[-2].shape == 'd' and kline.low < self._PenPointList[-2].value):
                    self._PenPointList.pop()
                    Toolkit.updatePen(self._PenPointList,
                                      -1,
                                      kline.idx,
                                      kline.high if self._PenPointList[-1].shape == 'u' else kline.low)
                    return True
            else:
                Toolkit.append(self._PenPointList,
                               PenPoint(kidx=kline.idx,
                                        shape=kline.shape,
                                        value=kline.high if kline.shape == 'u' else kline.low))
                return True
        return False



def resample(timedelta, df):
    times = int(math.ceil(pd.Timedelta(timedelta) / (df.ikidx[1].name - df.ikidx[0].name)))
    newdf = pd.DataFrame(columns=df.columns)
    for i in xrange(0, df.shape[0], times):
        end = i + times
        end = end if end <= df.shape[0] else df.shape[0]
        newdf.kidx[df.ix[end - 1].name] = {'high': max(df[i:i + times].high.values),
                                          'low': min(df[i:i + times].low.values)}
    return newdf


def addLineDf(ax, df, **kwargs):
    for i in xrange(df.shape[0]):
        itDf = df.ix[i]
        vline = Line2D(xdata=(i+0.5, i+0.5), ydata=(itDf['low'], itDf['high']), linewidth = 3, **kwargs)
        ax.add_line(vline)

        #标识顶/底分型
        if 'shape' in itDf:
            if itDf['shape'] == 'u':
                ax.text(i+0.5, itDf['high'], 'u', color = 'r')
            elif itDf['shape'] == 'd':
                ax.text(i+0.5, itDf['low'], 'd', color = 'g')

    ax.grid(True)
    ax.autoscale_view()

def addLine1(ax, list, **kwargs):
    for i in xrange(len(list)):
        item = list[i]
        vline = Line2D(xdata=(i + 0.5, i + 0.5), ydata=(item.low, item.high), linewidth=3, **kwargs)
        ax.add_line(vline)

        # 标识顶/底分型
        if item.shape:
            if item.shape == 'u':
                ax.text(i + 0.5, item.high, 'u', color='r')
            elif item.shape == 'd':
                ax.text(i + 0.5, item.low, 'd', color='g')

    ax.grid(True)
    ax.autoscale_view()


def addPen(ax, list, **kwargs):
    # df.ikidx[int(list.ikidx[0]['kidx'])].high
    if len(list) < 2:
        return
    for i in xrange(len(list) - 1):
        itPen1 = list[i]
        itPen2 = list[i + 1]
        vline = Line2D(xdata=(itPen1.kidx, itPen2.kidx), ydata=(itPen1.value, itPen2.value), **kwargs)
        ax.add_line(vline)
        ax.text(itPen1.kidx, itPen1.value, i, color='cyan', fontsize='10')
    indexLast = len(list) - 1
    ax.text(list[indexLast].kidx, list[indexLast].value, indexLast, color='cyan', fontsize='10')
    ax.autoscale_view()

# def addLine(ax, line, pen, **kwargs):
#     if len(line) < 2 or len(pen) < 2:
#         return
#     for i in xrange(len(line) - 1):
#         itLine1

def addLine1_(ax, df, **kwargs):
    id1, id2 = 3, 10
    itDf1 = df.ix[id1]
    itDf2 = df.ix[id2]
    vline = Line2D(xdata=(id1 + 0.5, id2 + 0.5), ydata=(itDf1.high, itDf2['low']), color='g')
    ax.add_line(vline)
    ax.text(id2 + 0.5, itDf2['low'], '^')


def no_picture():
    st = nanotime.now()

    dft = df5mKline[['high', 'low']]
    ch = Chan(True)
    for i in xrange(dft.shape[0]):
        ch.onNewKline(dft.iloc[i])

    print ('ch cost:%d' % (nanotime.now() - st).milliseconds())

    #print ch._KlineList
    #print ch._LinePointList
    #print tw.getSequence()


def picture1():
    st = nanotime.now()
    fig, ax = plt.subplots(3, 1)
    dft = df5mKline[['high', 'low']]
    # dft = resample('30min',dft)

    ch = Chan(True)
    for i in xrange(dft.shape[0]):
        ch.onNewKline(dft.iloc[i])

    ax[0].set_title(u'原始数据')
    ax[1].set_title(u'处理包含关系并生成笔')
    ax[2].set_title(u'上一图中的笔')
    addLineDf(ax[0], dft, color='b')
    addLine1(ax[1], ch._KlineList, color='b')
    addPen(ax[1], ch._PenPointList, color='r')
    addPen(ax[2], ch._PenPointList, color='g', linestyle="-.")
    addPen(ax[2], [ch._PenPointList[lp.pidx] for lp in ch._LinePointList], color='b')


    #print ch._PenPointList
    print ('ch cost:%d' % (nanotime.now() - st).milliseconds())
    print ch._LinePointList
    plt.show()

def picture3():
    dft = df5mKline[['high', 'low']]
    # dft = resample('30min',dft)
    ch = Chan(True)
    for i in xrange(dft.shape[0]):
        fig, ax = plt.subplots(1, 1)
        ch.onNewKline(dft.ix[i])
        addLine1(ax, ch._KlineList, color='b')
        addPen(ax, ch._PenPointList, color='r')
        plt.show()


def addLine2(ax, df, **kwargs):
    for i in xrange(df.shape[0]):
        itDf = df.ix[i]
        vline = Line2D(xdata=(dt.date2num(itDf.name), dt.date2num(itDf.name)), ydata=(itDf['low'], itDf.high),
                       linewidth=5, **kwargs)
        ax.add_line(vline)
        ax.autoscale_view()


def picture2():
    fig, ax = plt.subplots(2, 1)
    fig.subplots_adjust(bottom=0.2)
    dft = df5mKline[['high', 'low']]
    addLine2(ax[0], dft)

    tw = Chan(True)
    for i in xrange(dft.shape[0]):
        tw.onNewKline(dft.ix[i])

    addLine2(ax[1], tw.getdf(), color='r')

    # mondays = WeekdayLocator(MONDAY)        # major ticks on the mondays
    # alldays = MinuteLocator(interval=5)              # minor ticks on the days
    # weekFormatter = DateFormatter('%b %d')  # e.g., Jan 12
    # dayFormatter = DateFormatter('%d')      # e.g., 12
    # minuteFormatter = DateFormatter('%H:%M')

    autodates = AutoDateLocator()
    for _ax in ax:
        _ax.xaxis.set_major_kidxator(DayLocator())
        _ax.xaxis.set_minor_kidxator(MinuteLocator(interval=30))
        _ax.xaxis.set_major_formatter(DateFormatter('%m/%d'))
        _ax.xaxis.set_minor_formatter(DateFormatter('%H:%M'))
        _ax.xaxis_date()
        _ax.autoscale_view()

    plt.setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')
    plt.show()


#no_picture()
picture1()
