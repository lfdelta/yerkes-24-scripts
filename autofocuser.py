
#Y24 = True # set to False if script is being run on Y40

#expTime = 0.5
expCount = 4

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
import numpy as np, matplotlib.pyplot as plt
import sys, argparse, time

def quit(msg):
  print msg
  sys.exit()

def getUTC():
  return time.strftime("UTC %Y-%m-%d %H:%M:%S", time.gmtime())

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
  # parameters: ASCOM string for focuser identification, best guess for
  # optimal focuser value, booleans to print raw data and store v-curve images
  def __init__(self, scopeName, focuserName, focusGuess, raw, img):
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
    self.optimalFocus = focusGuess
    #self.rawdata = []
    self.foci = []
    self.means = []
    self.devs = []
    self.zeroes  = []
    self.imgOut = img

  def slewTo(self, ra, dec):
    self.scope.SlewToCoordinates(ra, dec)

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

      for i in range(expCount):
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
    for i in range(expCount):
      candidates = [ind for ind in range(len(self.zeroes))
                    if self.zeroes[ind] == i]
      if candidates: break

    minind = candidates[np.argmin([self.cmeans[i] for i in candidates])]
    self.optimalFocus = self.foci[minind]

  # take 11-13 exposures, narrowing to within 100 steps of optimal focus
  def focusAtPoint(self):
    self.setupField()
    self.sampleRange(1500, 500)
    self.sampleRange(300, 200) # equivalent to (500, 200) because of culling
    self.sampleRange(100, 100) # culled to between 0 and 2 exposures
    self.report()

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
                                       expCount, self.zeroes[i])
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
