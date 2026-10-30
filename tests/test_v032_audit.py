import unittest
from types import SimpleNamespace as NS
import numpy as np
import pandas as pd
from plateverif.config import Config
from plateverif.matching import Pins, PinMatch
from plateverif.verify import _World, _decide, _frontage_match
from plateverif.statuses import Status

class AuditTests(unittest.TestCase):
    def fixture(self, side='right'):
        pins=Pins(np.array([0.,30.]),np.zeros(2),np.array(['9','3']),np.array(['A','A']),np.zeros(2))
        addr=pd.DataFrame({'side':['right',side],'label':['9 A','3 A'],'street_display':['A','A']})
        w=_World(addr,pins,np.array([[0.,-10.]]),np.array([[1.,0.]]))
        p=NS(match=PinMatch(0,0.,'position',1),reading='3',location=np.zeros(2),seqs=[1,2],tri=object(),agreement=1.,mean_det_conf=.9,mean_ocr_conf=.95,side='right',votes={})
        c=Config();c.decision.strict_error_claims=True
        return p,w,c
    def test_strong_out_of_place_retained(self):
        p,w,c=self.fixture();_decide(p,w,c);self.assertEqual(p.status,Status.OUT_OF_PLACE)
    def test_weak_errors_demoted(self):
        for side in ('right','left'):
            for field,val in [('seqs',[1]),('tri',None),('agreement',.7),('mean_ocr_conf',.7)]:
                with self.subTest(side=side,field=field):
                    p,w,c=self.fixture(side);setattr(p,field,val);_decide(p,w,c);self.assertEqual(p.status,Status.UNCERTAIN)
    def test_strong_wrong_side_retained(self):
        p,w,c=self.fixture('left');_decide(p,w,c);self.assertEqual(p.status,Status.WRONG_SIDE)
    def test_frontage_corner_rejected(self):
        p,w,c=self.fixture();w.pins.x[:]=[20.,11.];w.pins.streets[:]=['B','A'];p.match=PinMatch(None,None,'none',0)
        c.matching.frontage_match_max_m=25;_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
