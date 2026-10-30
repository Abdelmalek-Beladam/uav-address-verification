import unittest
from types import SimpleNamespace as NS
import numpy as np
import pandas as pd
from plateverif.config import Config
from plateverif.matching import PinMatch, Pins
from plateverif.verify import _relaxed_match

class RelaxedTests(unittest.TestCase):
    def setup_case(self, xy=((8.,0.),), keys=('12',), streets=('A',), sides=('left',)):
        cfg=Config(); cfg.matching.relaxed_match_distance_m=12
        world=NS(pins=Pins(np.array(xy)[:,0],np.array(xy)[:,1],np.array(keys),np.array(streets),np.zeros(len(xy))),addr=pd.DataFrame({'side':sides}))
        plate=NS(match=PinMatch(None,None,'none',0),reading='12',seqs=[1,2],agreement=1.,mean_det_conf=.85,mean_ocr_conf=.95,location=np.array([0.,0.]),side='left',tri=object())
        return plate,world,cfg
    def test_accept(self):
        p,w,c=self.setup_case();_relaxed_match(p,w,c);self.assertEqual(p.match.pin,0)
    def test_far(self):
        p,w,c=self.setup_case(xy=((12.1,0.),));_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_one_photo(self):
        p,w,c=self.setup_case();p.seqs=[1,1];_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_low_ocr(self):
        p,w,c=self.setup_case();p.mean_ocr_conf=.6;_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_disagreement(self):
        p,w,c=self.setup_case();p.agreement=.7;_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_wrong_side(self):
        p,w,c=self.setup_case(sides=('right',));_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_conflicting_address(self):
        p,w,c=self.setup_case(xy=((8.,0.),(2.,0.)),keys=('12','14'),streets=('A','A'),sides=('left','left'));_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_junction(self):
        p,w,c=self.setup_case(xy=((8.,0.),(9.,0.)),keys=('12','14'),streets=('A','B'),sides=('left','left'));_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_duplicate_number(self):
        p,w,c=self.setup_case(xy=((8.,0.),(9.,0.)),keys=('12','12'),streets=('A','A'),sides=('left','left'));_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_keep_existing(self):
        p,w,c=self.setup_case();p.match=PinMatch(1,1.,'existing',1);_relaxed_match(p,w,c);self.assertEqual(p.match.pin,1)
    def test_default_off(self):
        p,w,c=self.setup_case();c.matching.relaxed_match_distance_m=0;_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)

    def test_requires_triangulation(self):
        p,w,c=self.setup_case();p.tri=None;_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_corner_guard_covers_frontage_radius(self):
        p,w,c=self.setup_case(xy=((8.,0.),(20.,0.)),keys=('12','14'),streets=('A','B'),sides=('left','left'))
        c.matching.frontage_match_max_m=25;_relaxed_match(p,w,c);self.assertIsNone(p.match.pin)
