# -*- coding: utf-8 -*-

from mutatorMath.objects.error import MutatorError
from mutatorMath.objects.location import Location, sortLocations, biasFromLocations

import sys

__all__ = ['Mutator', 'buildMutator']

_EPSILON = sys.float_info.epsilon

def buildMutator(items):
    """
        Build a mutator with the (location, obj) pairs in items.
        Determine the bias based on the given locations.
    """
    m = Mutator()
    # the order itself does not matter, but we should always build in the same order.
    items.sort()
    bias = biasFromLocations([loc for loc, obj in items], True)
    m.setBias(bias)
    n = None
    ofx = []
    onx = []
    for loc, obj in items:
        if (loc-bias).isOrigin():
            m.setNeutral(obj)
            break
    if m.getNeutral() is None:
        raise MutatorError("Did not find a neutral for this system", m)
    for loc, obj in items:
        lb = loc-bias
        if lb.isOrigin(): continue
        if lb.isOnAxis():
            onx.append((lb, obj-m.getNeutral()))
        else:
            ofx.append((lb, obj-m.getNeutral()))
    for loc, obj in onx:
        m.addDelta(loc, obj, punch=False,  axisOnly=True)
    for loc, obj in ofx:
        m.addDelta(loc, obj, punch=True,  axisOnly=True)
    return bias, m
    

class Mutator(dict):
    
    """ 
        Calculator for multi dimensional interpolations.
    
    ::
        
        # The mutator needs one neutral object.
        m = Mutator(myNeutralMathObject)
        
        # The mutator needs one or more deltas.
        m.addDelta(Location(pop=1), myMasterMathObject-myNeutralMathObject)
        
        # The mutator calculates instances at other locations. Remember to inflate.
        m.getInstance(Location(pop=0.5)) + myNeutralMathObject
    
    """

    def __init__(self, neutral=None):
        self._axes = {}
        self._tags = {}
        self._neutral = neutral
        self._bias = Location()
    
    def setBias(self, bias):
        self._bias = bias

    def getBias(self, bias):
        return self._bias

    def setNeutral(self, aMathObject, deltaName="origin"):
        """Set the neutral object."""
        self._neutral = aMathObject
        self.addDelta(Location(), aMathObject-aMathObject, deltaName, punch=False, axisOnly=True)
    
    def getNeutral(self):
        """Get the neutral object."""
        return self._neutral
        
    def addDelta(self, location, aMathObject, deltaName = None, punch=False,  axisOnly=True):
        """ Add a delta at this location.
            *   location:   a Location object
            *   mathObject: a math-sensitive object
            *   deltaName: optional string/token
            *   punch:
                *   True: add the difference with the instance value at that location and the delta
                *   False: just add the delta.
        """
        if punch:
            r = self.getInstance(location, axisOnly=axisOnly)
            if r is not None:
                self[location.asTuple()] = aMathObject-r, deltaName
            else:
                raise mutator.error.MutatorError()
        else:
            self[location.asTuple()] = aMathObject, deltaName
                
    #
    # info
    #       
    
    def getAxisNames(self):
        """
            Collect a list of axis names from all deltas.
        """
        s = {}
        for l, x in self.items():
            s.update(dict.fromkeys([k for k, v in l], None))
        return s.keys()
        
    def _collectAxisPoints(self):
        """ 
            Return a dictionary with all on-axis locations.
        """
        for l, (value, deltaName) in self.items():
            location = Location(l)
            name = location.isOnAxis()
            if name is not None and name is not False:
                if not self._axes.has_key(name):
                    self._axes[name] = []
                if l not in self._axes[name]:
                    self._axes[name].append(l)
        return self._axes
    
    def _collectOffAxisPoints(self):
        """
            Return a dictionary with all off-axis locations.
        """
        offAxis = {}
        for l, (value, deltaName) in self.items():
            location = Location(l)
            name = location.isOnAxis()
            if name is None or name is False:
                offAxis[l] = 1
        return offAxis.keys()
    

    def collectLocations(self):
        """
            Return a dictionary with all objects.
        """
        pts = []
        for l, (value, deltaName) in self.items():
            pts.append(Location(l))
        return pts
                
    def _allLocations(self):
        """
            Return a list of all locations of all objects.
        """
        l = [] 
        for locationTuple in self.keys():
            l.append(Location(locationTuple))
        return l
            
    #
    #   get instances
    #

    def getInstance(self, aLocation, axisOnly=False, getFactors=False):
        """ Calculate the delta at aLocation.
            *   aLocation:  a Location object
            *   axisOnly:
                *   True: calculate an instance only with the on-axis masters.
                *   False: calculate an instance with on-axis and off-axis masters.
            *   getFactors:
                *   True: return a list of the calculated factors.
        """
        self._collectAxisPoints()
        factors = self.getFactors(aLocation, axisOnly)
        total = None
        for f, item, name in factors:
            if total is None:
                total = f * item
                continue
            total += f * item
        if total is None:
            total = 0 * self._neutral
        if getFactors:
            return total, factors
        return total

    def makeInstance(self, aLocation):
        """ 
            Calculate an instance with the right bias and add the neutral. 
        """
        if not aLocation.isAmbivalent():
            instanceObject = self.getInstance(aLocation-self._bias)
        else:
            locX, locY = aLocation.split()
            instanceObject = self.getInstance(locX-self._bias)*(1,0)+self.getInstance(locY-self._bias)*(0,1)
        return instanceObject+self._neutral

    def getFactors(self, aLocation, axisOnly=False):
        """
            Return a list of all factors and math items at aLocation.
            factor, mathItem, deltaName
        """
        deltas = []
        aLocation.expand(self.getAxisNames())
        limits = getLimits(self._allLocations(), aLocation)
        for deltaLocationTuple, (mathItem, deltaName) in sorted(self.iteritems()):
            deltaLocation = Location(deltaLocationTuple)
            deltaLocation.expand( self.getAxisNames())
            factor = self._accumulateFactors(aLocation, deltaLocation, limits, axisOnly)
            if not (factor-_EPSILON < 0 < factor+_EPSILON):
                # only add non-zero deltas.
                deltas.append((factor, mathItem, deltaName))    
        deltas.sort()
        deltas.reverse()
        return deltas

    #
    #   calculate
    #

    def _accumulateFactors(self, aLocation, deltaLocation, limits, axisOnly):
        """
            Calculate the factors of deltaLocation towards aLocation,
        """
        relative = []
        deltaAxis = deltaLocation.isOnAxis()
        if deltaAxis is None:
            relative.append(1)
        elif deltaAxis:
            deltasOnSameAxis = self._axes.get(deltaAxis, None)
            d = ((deltaAxis, 0),)
            if d not in deltasOnSameAxis:
                deltasOnSameAxis.append(d)
            if len(deltasOnSameAxis) == 1:
                relative.append(aLocation[deltaAxis] * deltaLocation[deltaAxis])
            else:
                factor =  self._calcOnAxisFactor(aLocation, deltaAxis, deltasOnSameAxis, deltaLocation)
                relative.append(factor)
        elif not axisOnly:
            factor = self._calcOffAxisFactor(aLocation, deltaLocation, limits)
            relative.append(factor)
        if not relative:
            return 0
        f = None
        for v in relative:
            if f is None: f = v
            else:
                f *= v
        return f

    def _calcOnAxisFactor(self, aLocation, deltaAxis, deltasOnSameAxis, deltaLocation):
        """ 
            Calculate the on-axis factors.
        """
        if deltaAxis == "origin":
            f = 0
            v = 0
        else:
            f = aLocation[deltaAxis]
            v = deltaLocation[deltaAxis]
        i = []
        iv = {}
        for value in deltasOnSameAxis:
            iv[Location(value)[deltaAxis]]=1
        i = iv.keys()
        i.sort()
        r = 0
        B, M, A = [], [], []
        mA, mB, mM = None, None, None
        for value in i:
            if value < f: B.append(value)
            elif value > f: A.append(value)
            else: M.append(value)
        if len(B) > 0:
            mB = max(B)
            B.sort()
        if len(A) > 0:
            mA = min(A)
            A.sort()
        if len(M) > 0:
            mM = min(M)
            M.sort()
        if mM is not None:
            if ((f-_EPSILON <  v) and (f+_EPSILON > v)) or f==v: r = 1
            else: r = 0
        elif mB is not None and mA is not None:
            if v < mB or v > mA: r = 0
            else:
                if v == mA:
                    r = float(f-mB)/(mA-mB)
                else:
                    r = float(f-mA)/(mB-mA)
        elif mB is None and mA is not None:
            if v==A[1]:
                r = float(f-A[0])/(A[1]-A[0])
            elif v == A[0]:
                r = float(f-A[1])/(A[0]-A[1])
            else:
                r = 0
        elif  mB is not None and mA is None:
            if v == B[-2]:
                r = float(f-B[-1])/(B[-2]-B[-1])
            elif v == mB:
                r = float(f-B[-2])/(B[-1]-B[-2])
            else:
                r = 0
        return r

    def _calcOffAxisFactor(self, aLocation, deltaLocation, limits):
        """ 
            Calculate the off-axis factors.
        """
        relative = []
        for dim in limits.keys():
            f = aLocation[dim]
            v = deltaLocation[dim]
            mB, M, mA = limits[dim]
            r = 0
            if mA is not None and v > mA:
                relative.append(0)
                continue
            elif mB is not None and v < mB:
                relative.append(0)
                continue
            if f < v-_EPSILON:
                if mB is None:
                    if M is not None and mA is not None:
                        if v == M:
                            r = (float(max(f,mA)-min(f, mA))/float(max(M,mA)-min(M, mA)))
                        else:
                            r = -(float(max(f,mA)-min(f, mA))/float(max(M,mA)-min(M, mA)) -1)
                    else: r = 0
                elif mA is None: r = 0
                else: r = float(f-mB)/(mA-mB)
            elif f > v+_EPSILON:
                if mB is None: r = 0
                elif mA is None:
                    if M is not None and mB is not None:
                        if v == M:
                            r = (float(max(f,mB)-min(f, mB))/(max(mB, M)-min(mB, M)))
                        else:
                            r = -(float(max(f,mB)-min(f, mB))/(max(mB, M)-min(mB, M)) - 1)
                    else: r = 0
                else: r = float(mA-f)/(mA-mB)
            else: r = 1
            relative.append(r)
        f = 1
        for i in relative:
            f *= i
        return f

def getLimits(locations, current, sortResults=True, verbose=False):
    """ 
        Find the projections for each delta in the list of locations, relative to the current location.
        Return only the dimensions that are relevant for current. 
    """
    limit = {}
    for l in locations:
        a, b = current.common(l)
        if a is None:
            continue
        for name, value in b.items():
            f = a[name]
            if not limit.has_key(name):
                limit[name] = {}
                limit[name]['<'] = {}
                limit[name]['='] = {}
                limit[name]['>'] = {}
                if f > 0:
                    limit[name]['>'] = {0: [Location()]}
                elif f<0:
                    limit[name]['<'] = {0: [Location()]}
                else:
                    limit[name]['='] = {0: [Location()]}
            if current[name] < value - _EPSILON:
                if not limit[name]["<"].has_key(value):
                    limit[name]["<"][value] = []
                limit[name]["<"][value].append(l)
            elif current[name] > value + _EPSILON:
                if not limit[name][">"].has_key(value):
                    limit[name][">"][value] = []
                limit[name][">"][value].append(l)
            else:
                if not limit[name]["="].has_key(value):
                    limit[name]["="][value] = []
                limit[name]["="][value].append(l)
    if not sortResults:
        return limit
    # now we have all the data, let's sort to the relevant values
    l = {}
    for name, lims in  limit.items():
        less = []
        more = []
        if lims[">"].keys():
            less = lims[">"].keys()
            less.sort()
            lim_min = less[-1]
        else:
            lim_min = None
        if lims["<"].keys():
            more = lims["<"].keys()
            more.sort()
            lim_max = more[0]
        else:
            lim_max = None
        if lim_min is None and lim_max is not None:
            # extrapolation < min
            if len(limit[name]['='])>0:
                l[name] = (None,  limit[name]['='].keys()[0], None)
            elif len(more) > 1 and len(limit[name]['='])==0:
                # extrapolation
                l[name] = (None,  more[0], more[1])
        elif lim_min is not None and lim_max is None:
            # extrapolation < max
            if len(limit[name]['='])>0:
                # less > 0, M > 0, more = None
                # -> end of a limit
                l[name] = (None, limit[name]['='], None)
            elif len(less) > 1 and len(limit[name]['='])==0:
                # less > 0, M = None, more = None
                # extrapolation
                l[name] = (less[-2], less[-1], None)
        else:
            if len(limit[name]['=']) > 0:
                l[name] = (None,  limit[name]['='].keys()[0], None)
            else:
                l[name] = (lim_min,  None, lim_max)
    return l
        
if __name__ == "__main__":
    def test_singleAxis(n):
        """
        Tests for a single axis.
        A mutator is created with a single value, 100, on a single axis.

        values we enter should be reproduced
        >>> test_singleAxis(1)
        100.0
        >>> test_singleAxis(0)
        0

        a value in the middle should be in the middle
        >>> test_singleAxis(.5)
        50.0
        >>> test_singleAxis(.99)
        99.0

        extrapolation over zero
        >>> test_singleAxis(-1)
        -100.0
        >>> test_singleAxis(-2)
        -200.0
        >>> test_singleAxis(-1.5)
        -150.0

        extrapolation over value
        >>> test_singleAxis(2)
        200.0

        """
        m = Mutator()
        neutral = 0
        value = 100.0
        m.setNeutral(neutral-neutral)
        m.addDelta(Location(pop=1), value-neutral, deltaName="test")
        return m.getInstance(Location(pop=n)) + neutral

    def test_twoAxes(l, n):
        """Test for a system with two axes, 2 values both on-axis.

        >>> test_twoAxes(1, 1)
        0.0
        >>> test_twoAxes(1, 0)
        100.0
        >>> test_twoAxes(0, 1)
        -100.0
        >>> test_twoAxes(2, 0)
        200.0
        >>> test_twoAxes(0, 2)
        -200.0

        a value in the middle should be in the middle
        """
        m = Mutator()
        neutral = 0
        value = 100.0
        m.setNeutral(neutral-neutral)
        m.addDelta(Location(pop=1), value-neutral, deltaName="test1")
        m.addDelta(Location(snap=1), -1*value-neutral, deltaName="test2")
        return m.getInstance(Location(pop=l, snap=n)) + neutral

    def test_twoAxesOffAxis(l, n):
        """Test for a system with two axes. Three values, two on-axis, one off-axis.

        >>> test_twoAxesOffAxis(0, 0)
        0
        >>> test_twoAxesOffAxis(1, 1)
        50.0
        >>> test_twoAxesOffAxis(2, 2)
        200.0
        >>> test_twoAxesOffAxis(1, 0)
        100.0
        >>> test_twoAxesOffAxis(0, 1)
        -100.0
        >>> test_twoAxesOffAxis(2, 0)
        200.0
        >>> test_twoAxesOffAxis(0, 2)
        -200.0

        a value in the middle should be in the middle
        """
        m = Mutator()
        neutral = 0
        value = 100.0
        m.setNeutral(neutral-neutral)
        m.addDelta(Location(pop=1), value-neutral, deltaName="test1")
        m.addDelta(Location(snap=1), -1*value-neutral, deltaName="test2")
        m.addDelta(Location(pop=1, snap=1), 50, punch=True, deltaName="test2")
        return m.getInstance(Location(pop=l, snap=n)) + neutral
    
    def test_twoAxesOffAxisSmall(l, n):
        """Test for a system with two axes. Three values, two on-axis, one off-axis.
        >>> test_twoAxesOffAxisSmall(0, 0)
        0
        >>> test_twoAxesOffAxisSmall(1, 1)
        5e-16
        >>> test_twoAxesOffAxisSmall(2, 2)
        2e-15
        >>> test_twoAxesOffAxisSmall(1, 0)
        1e-15
        >>> test_twoAxesOffAxisSmall(0, 1)
        -1e-15
        >>> test_twoAxesOffAxisSmall(2, 0)
        2e-15
        >>> test_twoAxesOffAxisSmall(0, 2)
        -2e-15

        a value in the middle should be in the middle
        """
        m = Mutator()
        neutral = 0
        value = 1e-15
        m.setNeutral(neutral-neutral)
        m.addDelta(Location(pop=1), value-neutral, deltaName="test1")
        m.addDelta(Location(snap=1), -1*value-neutral, deltaName="test2")
        m.addDelta(Location(pop=1, snap=1), 0.5*value-neutral, punch=True, deltaName="test2")
        return m.getInstance(Location(pop=l, snap=n)) + neutral
    
    def test_getLimits(a, b, t):
        """Test the getLimits function
        >>> test_getLimits(0, 1, 0)   
        {'pop': (None, 0, None)}
        >>> test_getLimits(0, 1, 0.5)   
        {'pop': (0, None, 1)}
        >>> test_getLimits(0, 1, 1)   
        {'pop': (None, {1: [<Location pop:1 >]}, None)}
        """
        la = Location(pop=a)
        lb = Location(pop=b)
        locations = [la, lb]
        test  = Location(pop=t)
        print(getLimits(locations, test))
    
    def test_methods():
        """ Test some of the methods.
        >>> m = test_methods()
        >>> m.getAxisNames()
        ['snap', 'pop']
        """
        m = Mutator()
        neutral = 0
        value = 100.0
        m.setNeutral(neutral-neutral)
        m.addDelta(Location(pop=1), value-neutral, deltaName="test1")
        m.addDelta(Location(snap=1), -1*value-neutral, deltaName="test2")
        m.addDelta(Location(pop=1, snap=1), 50, punch=True, deltaName="test2")
        return m

    def test_builder():
        """ Test the mutator builder.

        >>> items = [
        ...    (Location(pop=1, snap=1), 1),
        ...    (Location(pop=2, snap=1), 2),
        ...    (Location(pop=3, snap=1), 3),
        ...    (Location(pop=1, snap=2), 4),
        ...    (Location(pop=2, snap=2), 5),
        ...    (Location(pop=3, snap=2), 6),
        ... ]
        >>> bias, mb = buildMutator(items)
        >>> bias
        <Location pop:1, snap:1 >
        >>> mb.makeInstance(Location(pop=1, snap=1))
        1
        >>> mb.makeInstance(Location(pop=1, snap=2))
        4
        >>> mb.makeInstance(Location(pop=3, snap=2))
        6
        >>> mb.makeInstance(Location(pop=3, snap=1.5))
        4.5
        """

        
    def _test():
        import doctest
        doctest.testmod()

    _test()
