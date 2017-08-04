
#Y24 = True # set to False if script is being run on Y40

#expTime = 0.5
#expCount = 4

#focGuess = 6000 # best guess for focuser value; tests within +/- 1500 steps

############################################################################
## Automatically takes a series of exposures via MaximDL and extracts the ##
##  full width at half maximum. Exposures are recorded over a series of   ##
##  focus values to plot a V curve and find the minimum (optimum) focus.  ##
##      Prints CSV data to stdout and plots V curve using matplotlib.     ##
##                                                                        ##
##    Designed for use with Python 2.7 on the Windows operating system.   ##
##                                                                        ##
##                           Yerkes Observatory                           ##
############################################################################

# definitions
from win32com.client import Dispatch
import numpy as np
import matplotlib.pyplot as plt
import astropy.time as aptime
import astropy.units as apu
import sys, '''argparse,''' time

def quit(msg):
  print msg
  sys.exit()

def getUTC():
  return time.strftime("UTC %Y-%m-%d %H:%M:%S", time.gmtime())

class Coordinate:
  def __init__(self, ra, dec):
    self.RA = ra
    self.Dec = dec
  def __repr__(self):
    return "{%f, %f}" % (self.RA, self.Dec)

class ExposureData:
  def __init__(self, focusval):
    self.focus = focusval
    self.fwhm = []
  def process(self):
    data = [x for x in self.fwhm if x > 0] # don't analyze bad data
    self.zerocount = len(self.fwhm) - len(data) # number of bad exposures
    if data == []:
      self.mean = self.stdev = -1
    else:
      self.mean = np.mean(data)
      self.stdev = np.std(data)

class AutoFocuser:
  # establish connections to CCD (via MaximDL) and focuser
  # parameters: ASCOM string for focuser identification, best guess for optimal
  # focuser value, and booleans to print raw data and store v-curve images
  def __init__(self, scopeName, focuserName, focusGuess, expCount, raw, img):
    self.scope = Dispatch(scopeName)
    self.scope.Connected = True
    if not self.scope.Connected: quit("Telescope failed to connect")
    if not self.scope.CanSlew:
      quit("Telescope does not support programmed slewing")
    if self.scope.CanSetTracking: self.scope.Tracking = True

    self.cam = Dispatch("MaxIm.CCDCamera")
    self.cam.linkEnabled = True
    if not self.cam.LinkEnabled: quit("Camera failed to connect")
    self.cam.BinX = self.cam.BinY = 2
    
    self.focuser = Dispatch(focuserName)
    self.focuser.Connected = True
    if not self.focuser.Connected:
      quit("Focuser failed to connect")
    if not self.focuser.Absolute:
      quit("Focuser does not support absolute positioning")

    self.expTime = 0.5
    self.expCount = expCount
    self.imgOut = img
    self.clearData()

  def clearData(self):
    self.optimalFocus = focusGuess
    #self.rawdata = []
    self.foci = []
    self.means = []
    self.devs = []
    self.zeroes  = []

  def slewTo(self, coord):
    self.scope.SlewToCoordinates(coord.RA, coord.Dec)

  def expose(self, t = self.expTime):
    while self.cam.CameraStatus != 2: continue # 2: "connected but inactive"
    self.cam.Expose(t, 1)
    time.sleep(0.1) # may not be long enough to prevent duplicates
    while self.cam.CameraStatus != 2: continue

  # establish a subframe of given dimensions (in pixels), centered at the
  # brightest pixel in the field
  def subframe(self, width, height):
    width = min(width, self.cam.CameraXSize) # don't subframe larger than full
    height = min(height, self.cam.CameraYSize)
    naiveX = self.cam.MaxPixelX - (width/2) # upper-left corner of subframe
    naiveY = self.cam.MaxPixelY - (height/2)
    lbX = max(0, naiveX) # set lower bound = 0
    lbY = max(0, naiveY)
    ubX = min(lbX, self.cam.CameraXSize - width) # set upper bound
    ubY = min(lbY, self.cam.CameraYSize - height)
    self.cam.StartX = ubX
    self.cam.StartY = ubY
    self.cam.NumX = width
    self.cam.NumY = height

  # subframe to star, then optimize exposure time (minimum 0.25s) to get
  # photon counts in the range of [10 000, 20 000]
  def setupField(self):
    self.cam.SetFullFrame()
    self.expose()
    self.subframe(100, 100)
    while (self.expTime > 0.25 or self.cam.MaxPixel < 10000
           or self.cam.MaxPixel > 20000):
      print "%d counts at %.3fs exposure" % (self.cam.MaxPixel, self.expTime)
      self.expTime = max(0.25, 15000.0 * self.expTime / self.cam.MaxPixel)
      self.expose()

  # take a series of exposures over the range of focuser values in
  # [optimal - reach, optimal + reach] with a point every 'prec' steps,
  # then store and analyze the data before running optimizeFocus
  def sampleRange(self, reach, prec):
    focRange = range(self.optimalFocus - reach,
                          self.optimalFocus + reach + 1, prec)
    focRange = [f for f in self.focRange if not f in self.foci]
    self.foci.extend(focRange) # append non-duplicate focus values

    for f in focRange:
      self.focuser.Move(f)
      tmpData = ExposureData(f)
      if self.raw: print "\nFocus: %d" % f
      while self.focuser.IsMoving: continue

      for i in range(self.expCount):
        self.expose()
        tmpData.fwhm.append(self.cam.FWHM if self.cam.FWHM else -1)
        if self.raw: print "FWHM: %.3f" % self.cam.FWHM

      tmpData.process()
      #self.rawdata.append(tmpData)
      self.foci.append(f)
      self.means.append(tmpData.mean)
      self.devs.append(tmpData.stdev)
      self.zeroes.append(tmpData.zerocount)
      self.optimizeFocus()

  # update the object's optimalFocus value based upon its current data
  def optimizeFocus(self):
    # isolate data indices which have the fewest number of bad exposures
    for i in range(self.expCount):
      candidates = [ind for ind in range(len(self.zeroes))
                    if self.zeroes[ind] == i]
      if candidates: break

    minind = candidates[np.argmin([self.cmeans[i] for i in candidates])]
    self.optimalFocus = self.foci[minind]

  # take 11-13 exposures, narrowing to within 100 steps of optimal focus
  def focusAtPoint(self, goto = None):
    self.clearData()
    if (goto): self.slewTo(goto)
    self.setupField()
    self.sampleRange(1500, 500)
    self.sampleRange(300, 200) # equivalent to (500, 200) because of culling
    self.sampleRange(100, 100) # culled to between 0 and 2 exposures
    #self.report()

  # print recorded data
  def report(self):
    utc = getUTC()
    print utc
    print "%f degC" % self.cam.AmbientTemperature
    print ("Focus,Mean FWHM(px), FWHM StdDev (px),",
           "Exposure (s),# Exposures,# Bad Exposures")
    for i in range(len(self.foci)):
      print "%d,%.3f,%.3f,%f,%d,%d" % (self.foci[i], self.means[i],
                                       self.devs[i], self.expTime,
                                       self.expCount, self.zeroes[i])
    print "Optimal focus value is %d" % self.optimalFocus
    sys.stdout.flush()

    # plot a V-curve, if requested
    if self.imgOut:
      self.drawPlot()
      self.fig.savefig(utc)

  # plot a V-curve based upon recorded data
  def drawPlot(self):
    self.fig, self.ax = plt.subplots()
    self.ax.set_xlabel("Focus")
    self.ax.set_ylabel("Mean\nFWHM", rotation=0)
    self.ax.errorbar(self.foci, self.means, yerr=self.devs,
                     c='g', lw=1, marker='o', mfc='lime', mec='g',
                     capsize=5, ecolor='k')

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
          return True
    return False

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

# calculate the local sidereal time, in hours
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


# parse command line arguments
#parser = argparse.ArgumentParser(description="V curve")
#parser.add_argument("-r", "--raw", action="store_true",
#                    help="print raw data as it is collected")
#parser.add_argument("-p", "--plot", action="store_true",
#                    help="plot the curve using matplotlib")
#parser.add_argument("-i", "--image", action="store_true",
#                    help="export v-curves to disk")
#args = parser.parse_args()

# setup
#focName = "ASCOM.FocusLynx.Focuser" if Y24 else "ASCOM.OptecTCF_S.Focuser"
#autofoc = AutoFocuser(focName, focGuess, args.raw, args.image)
