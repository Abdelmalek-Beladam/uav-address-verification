import unittest
from types import SimpleNamespace as NS
import numpy as np
import pandas as pd
from plateverif.config import Config
from plateverif.matching import PinMatch, Pins
from plateverif.verify import _frontage_match, _partial_read

class FrontageTests(unittest.TestCase):
    def case(self, xy=((11.,0.),(-25.,0.),(16.,8.)), keys=('3','1','5'), streets=('A','A','A'), sides=('right','right','right')):
        cfg=Config(); cfg.matching.frontage_match_max_m=25
        world=NS(pins=Pins(np.array(xy)[:,0],np.array(xy)[:,1],np.array(keys),np.array(streets),np.zeros(len(xy))),addr=pd.DataFrame({'side':sides}))
        plate=NS(match=PinMatch(None,None,'none',0),reading='3',seqs=[1,2],agreement=1.,mean_det_conf=.55,mean_ocr_conf=.99,
                 location=np.array([0.,0.]),side='right',tri=object())
        return plate,world,cfg
    def test_shop_front_accepted(self):
        p,w,c=self.case();_frontage_match(p,w,c);self.assertEqual(p.match.pin,0)
    def test_neighbour_closer_rejected(self):
        p,w,c=self.case(xy=((18.,0.),(11.,0.),(30.,0.)));_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_too_far(self):
        p,w,c=self.case(xy=((26.,0.),(-40.,0.),(40.,0.)));_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_one_photo(self):
        p,w,c=self.case();p.seqs=[1];_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_no_measured_position(self):
        p,w,c=self.case();p.tri=None;_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_low_ocr(self):
        p,w,c=self.case();p.mean_ocr_conf=.7;_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_other_side_only(self):
        p,w,c=self.case(sides=('left','right','right'));_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_same_number_two_places(self):
        p,w,c=self.case(xy=((11.,0.),(-12.,0.),(30.,0.)),keys=('3','3','5'),streets=('A','B','A'));_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_other_number_at_spot(self):
        p,w,c=self.case(xy=((11.,0.),(2.,0.),(30.,0.)),keys=('3','9','5'),sides=('right','left','right'));_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_default_off(self):
        p,w,c=self.case();c.matching.frontage_match_max_m=0;_frontage_match(p,w,c);self.assertIsNone(p.match.pin)
    def test_keep_existing(self):
        p,w,c=self.case();p.match=PinMatch(2,1.,'existing',1);_frontage_match(p,w,c);self.assertEqual(p.match.pin,2)

class PartialTests(unittest.TestCase):
    def test_cases(self):
        self.assertTrue(_partial_read('1','17')); self.assertTrue(_partial_read('5','15'))
        self.assertTrue(_partial_read('2','21')); self.assertTrue(_partial_read('21','121'))
        self.assertFalse(_partial_read('17','17')); self.assertFalse(_partial_read('3','17'))
        self.assertFalse(_partial_read('17','1')); self.assertFalse(_partial_read('7','5'))

if __name__=='__main__': unittest.main()
