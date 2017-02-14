import unittest
from turret import turret

class TestTurretMethods(unittest.TestCase):
    
    def testhostDel(self):
        self.assertTrue(t.hostDel('testunit.host'))

    def testhostAdd(self):
        self.assertTrue(t.hostAdd('testunit.host'))



if __name__ == "__main__":
    t = turret.Turret()

    unittest.main()

