import os.path 

class MyNotation(object):
    Value=('A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2')
    Direction=('N', 'E', 'S', 'W')

    def parseDeal(self,deal):
        first_hand=self.Direction.index(deal[0])
        distribution=[]
        hands=deal[2:].split()
        for hand in hands:
            suits=hand.split('.')
            for i,suit in enumerate(suits):
                for v in suit:
                    distribution.append(i*13+self.Value.index(v))
        if first_hand!=0:
            distribution=distribution[first_hand*13:]+distribution[:first_hand*13]
        return distribution
    
    def export(self):
        distribution=self.parseDeal(self.MTS['Deal'])
        contract=self.MTS['Contract']
        declarer=MyNotation.Direction.index(self.MTS['Declarer'])
        dealer=MyNotation.Direction.index(self.MTS['Dealer'])
        vuln=self.MTS['Vulnerable']
        result=self.MTS['Result']
        r=dict(declarer=declarer,
               contract=contract,
               distribution=distribution,
               dealer=dealer,
               vulnerable=vuln,
               result=result)
        return r

class PBN(object):
    def __init__(self,**kwds):
        '''A deal should be specified as follows:
        N:KT2.KQ8632.4.KJ3 J.T97.AKJT975.62 AQ964.54.Q3.QT94 8753.AJ.862.A875
        The suits in the order S H D C, separated by . A void is indicated by
        two sequential dots.

        Keywords:

        Contract,Declarer,Deal <= compulsary for cli specification
        Event=None
        Site=None
        Date=None
        Board=None
        West='W'
        North='N'
        East='E'
        South='S'
        Dealer=None
        Vulnerable='None'
        Result=None

        '''
        self.MTStags=['Contract','Declarer','Deal','Event','Site','Date','Board',\
                      'West','North','East','South','Dealer','Vulnerable','Result']

        self.MTS={}
        for k,v in kwds.iteritems():
            if k in self.MTStags:
                self.MTS[k]=v


class PbnLibrary:
    games=[]
    current=-1
    stride=1

    def __init__(self):
        pass

    @classmethod
    def advance_to_next_deal(cls):
        PbnLibrary.current+=PbnLibrary.stride

    def set_current_deal(self,deal_number):
        PbnLibrary.current=deal_number

    def set_stride(self,stride):
        PbnLibrary.stride=stride

    def _get_mts(self):
        if PbnLibrary.current<0:
            self.set_current_deal(0)
        mts=self.games[self.current].MTS
        return mts

    def get_dealstr(self):
        return self._get_mts()['Deal']

    def get_dealer(self):
        return ['N','E','S','W'].index(self._get_mts()['Dealer'])

    def get_vuln(self):
        return ['None','NS','EW','All'].index(self._get_mts()['Vulnerable'])

    def get_result(self):
        declarer=self._get_mts()['Declarer']
        contract=self._get_mts()['Contract']
        tricks_made=int(self._get_mts()['Result'])
        tricks_to_make=int(contract[0])+6
        result=tricks_made-tricks_to_make
        if result==0:
            result_str="made"
        elif result<0:
            result_str="%d"%(result)
        else:
            result_str="+%d"%(result)
        msg="Historic result deal: %d\n%s %s by %s"%(self.current,contract,result_str,declarer)
        return msg

    def importFile(self,filename,start_deal_number,stride=1):
        ''' imports a pbn file '''

        if os.path.exists(filename):
            fd=open(filename,'r')
            lines=fd.readlines()
            fd.close()
            pbn=PBN()
            for line in lines:
                tag,value=self.parseLine(line)
                if not tag:
                    continue
                if tag=='end':
                    PbnLibrary.games.append(pbn)
                    pbn=PBN()
                elif tag in pbn.MTStags:
                    pbn.MTS[tag]=value
            self.set_current_deal(start_deal_number)
            self.set_stride(stride)
            return len(PbnLibrary.games)
        else:
            return 0
    
    def parseLine(self,line):
        # skip any remarks
        line=line.strip()
        if line.startswith('%'):
            tag=None
            value=None
        elif line=="":
            tag="end"
            value=None
        else:
            if not (line.count('[')==line.count(']')==1):
                tag=None
                value=None
            else:
                s=line.index('[')
                e=line.index(']')
                if not e>s:
                    print "previous line was malformed"
                    tag=None
                    value=None
                tmp=line[s+1:e]
                words=tmp.split()
                tag=words[0]
                i=tmp.index('"')
                value=reduce(lambda x,y:x+y,tmp[i:],'').replace('"','')
        return tag,value

if __name__=='__main__':
    Tournament=PbnLibrary()
    print Tournament.importFile('/home/lucas/.pybridge/pbn/Islgbl19.pbn',0)
    g=Tournament.games[3]
