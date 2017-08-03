
#CATALOG = 'UCAC3.txt'
#OBS_LAT = 42.5704 # north latitude in degrees
#OBS_LON = -88.5563 # east longitude in degrees

# definitions
import numpy as np
import sys, time
import astropy.time as aptime
import astropy.units as apu

class Coordinate:
  def __init__(self, ra, dec):
    self.RA = ra
    self.Dec = dec
  def __repr__(self):
    return "{%f, %f}" % (self.RA, self.Dec)

# calculates the local sidereal time, in hours
def getLST(lon):
  now = aptime.Time.now()
  lst = now.sidereal_time('apparent', apu.quantity.Quantity(value = lon,
                                                            unit = apu.degree))
  return lst.value

# convert altitude and azimuth coordinates to right ascension and declination,
# given the latitude and longitude (all inputs and outputs in units of degrees)
# methodology extracted from the follow site:
# http://star-www.st-and.ac.uk/~fv/webnotes/chapter7.htm
def AAtoRD(alt, az, lat = OBS_LAT, lon = OBS_LON):
  alt = np.deg2rad(alt); az = np.deg2rad(az); lat = np.deg2rad(lat)
  lst = getLST(lon) * 15
  dec = np.arcsin(np.sin(alt)*np.sin(lat) + np.cos(alt)*np.cos(az)*np.cos(lat))
  ra = lst - np.rad2deg(np.arcsin(-np.cos(alt)*np.sin(az)/np.cos(dec)))
  return Coordinate(ra, np.rad2deg(dec))

# star catalog in the form of a hash table; 0.5-degree buckets by declination
# specifically tailored to the UCAC3 catalog used at Yerkes Observatory
# sections most likely to need adjustment are commented with a "###"
class Catalog:
  # an array with 219 "buckets", each of which is a linked list
  # (ls is initially non-empty to trick numpy into not creating a 2D array)
  def __init__(self, data=None):
    ls = [ [1] ]
    for i in range(219 - 1): ### nbuckets
      ls.append([])
    self.htbl = np.array(ls)
    self.htbl[0] = []
    if data: self.fill(data)

  # fills the catalog with {RA, Dec} coordinate objects from a text file
  def fill(self, filename):
    with open(filename) as f:
      bucket = 0
      nextdec = -19.5 ### declination upper bound for first bucket
      for line in f:
        ### "[%f, %f, %f, %f]" -> ["%f", "%f", "%f", "%f"] -> {%f, %f}
        tmp = line.strip("[]\n").split(", ")
        dec = float(tmp[1])
        coord = Coordinate(float(tmp[0]), dec)
        if dec > nextdec:
          nextdec += 0.5
          bucket += 1
        self.htbl[bucket].append(coord)

  # hash function: declination [-20, 89.5) -> bucket index [0, 218]
  def hashDec(self, dec):
    return int((dec - (dec % 0.5) + 0.5)*2 + 39) ###

  # returns True if the hash table and hash function are mismatched
  def checkHash(self):
    for i in range(self.htbl.size):
      for star in self.htbl[i]:
        if self.hashDec(star.Dec) != i:
          print "Hash table was formed incorrectly!"
          return True

  # takes a star catalog hash table and a target coordinate, and returns
  # the star Coordinate in the catalog which is nearest to the target
  def findNearestStar(self, coord):
    # isolate relevant bucket(s) in hash table
    bucket = self.hashDec(coord.Dec)
    if bucket < 0 or bucket > 218: ### max index ("know your data!")
      print "Bad coordinate %s passed to findNearestStar" % coord; return
    candidates = [x for x in self.htbl[bucket]]
    if coord.Dec % 0.5 < 0.1 and bucket != 0:
      candidates.extend([x for x in self.htbl[bucket - 1]])
    elif coord.Dec % 0.5 > 0.4 and bucket != 218: ### max index
      candidates.extend([x for x in self.htbl[bucket + 1]])

    # iterate through candidates with an accumulator
    nearestSqdist = np.inf
    nearestStar = None
    for star in candidates:
      rdist = star.RA - coord.RA
      ddist = star.Dec - coord.Dec
      sqdist = rdist*rdist + ddist*ddist
      if sqdist < nearestSqdist:
        nearestSqdist = sqdist
        nearestStar = star
    return nearestStar



#starRef = Catalog(CATALOG)
#starRef.checkHash()

# for quick interpreter testing
#def near(ra, dec):
#  print starRef.findNearestStar(Coordinate(ra, dec))

# write a script to:
# import the catalog, as here
# create a skygrid in alt/az coordinates
# connect to the telescope, camera, and focuser
# iterate through the grid in spiral or zig-zag (argument to choose which)
#   find the nearest star for a given alt/az coordinate
#   slew to that star
#   execute the vcurve script
#   export (alt, az, optimal focuser value) and maybe (temp)
#     alternatively, figure out how to store it and report all at once
