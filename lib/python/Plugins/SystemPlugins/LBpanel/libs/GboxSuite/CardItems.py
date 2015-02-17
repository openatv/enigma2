# 2014.10.12 15:50:17 CEST

class CardItem:

    def __init__(self, args):
        self.id = args[1]
        self.dyndns = args[3]
        self.provid = args[5]
        self.slot = args[7]
        self.level = args[9]
        self.dist = args[11]
        self.boxid = args[13]




class CardDisplayItem:

    def __init__(self, item):
        self.count = 1
        self.cardList = [item]



    def addItem(self, item):
        self.count = self.count + 1
        self.cardList.append(item)




