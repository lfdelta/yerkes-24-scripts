
Y24 = True # set to False if script is being run on Y40

#expTime = 0.5
expCount = 4

focGuess = 6000 # best guess for focuser value; tests within +/- 1500 units

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

class ExposureData:
  def __init__(self, focusval):
    self.focus = focusval
    self.fwhm = []
  def process(self):
    self.data = [x for x in self.fwhm if x > 0] # don't analyze bad data
    self.zerocount = len(self.fwhm) - len(self.data) # number of bad exposures
    if self.data == []:
      self.mean = self.stdev = -1
    else:
      self.mean = np.mean(self.data)
      self.stdev = np.std(self.data)

class AutoFocuser:
  # establish connections to CCD (via MaximDL) and focuser
  def __init__(self, focuserName, focusGuess):
    self.cam = Dispatch("MaxIm.CCDCamera")
    self.cam.linkEnabled = True
    if not self.cam.LinkEnabled: quit("Camera failed to connect")
    self.cam.BinX = self.cam.BinY = 2
    
    self.focuser = Dispatch(focuserName)
    self.focuser.Connected = True
    self.focuser.Link = True
    if not (focuser.Connected and focuser.Link):
      quit("Focuser failed to connect")
    if not focuser.Absolute:
      quit("Focuser does not support absolute positioning")

    self.expTime = 0.5
    self.optimalFocus = focusGuess
    #self.rawdata = []
    self.foci = []
    self.means = []
    self.devs = []
    self.zeroes  = []

  def expose(self):
    while self.cam.CameraStatus != 2: continue # 2: "connected but inactive"
    self.cam.Expose(self.expTime, 1)
    time.sleep(0.1) # may not be long enough to prevent duplicates
    while self.cam.CameraStatus != 2: continue

  def setupField(self):
    self.expose()
    self.subframe(100, 100)
    while (self.expTime > 0.25 or self.cam.MaxPixel < 10000
           or self.cam.MaxPixel > 20000):
      print "%d counts at %.3fs exposure" % (self.cam.MaxPixel, self.expTime)
      self.expTime = max(0.25, 15000.0 * self.expTime / self.cam.MaxPixel)
      self.expose()

  def subframe(self, width, height):
    self.cam.StartX = self.cam.MaxPixelX - (width / 2)
    self.cam.StartY = self.cam.MaxPixelY - (height / 2)
    self.cam.NumX = width
    self.cam.NumY = height

  # take a series of exposures over the range of focuser values in
  # [optimal - reach, optimal + reach] with a point every 'prec' units,
  # then store and analyze the data
  def sampleRange(self, reach, prec):
    self.focRange = range(self.optimalFocus - reach,
                          self.optimalFocus + reach + 1, prec)
    self.focRange = [f for f in self.focRange if not f in self.foci]
    self.foci.extend(self.focRange) # append non-duplicate focus values

    for f in self.focRange:
      self.focuser.Move(f)
      tmpData = ExposureData(f)
      if args.raw: print "\nFocus: %d" % f
      while self.focuser.IsMoving: continue

      for i in range(expCount):
        self.expose()
        tmpData.fwhm.append(self.cam.FWHM if self.cam.FWHM else -1)
        if args.raw: print "FWHM: %.3f" % self.cam.FWHM

      tmpData.process()
      #self.rawdata.append(tmpData)
      self.foci.append(f)
      self.means.append(tmpData.mean)
      self.devs.append(tmpData.stdev)
      self.zeroes.append(tmpData.zerocount)
      self.optimizeFocus

  def optimizeFocus(self):
    # isolate data indices which have the fewest number of bad exposures
    for i in range(expCount):
      candidates = [ind for ind in range(len(self.zeroes))
                    if self.zeroes[ind] == i]
      if candidates: break

    minind = candidates[np.argmin([self.cmeans[i] for i in candidates])]
    self.optimalFocus = self.foci[minind]

  # print recorded data
  def report(self):
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

  # plot a V-curve based upon recorded data
  def drawPlot(self):
    self.fig, self.ax = plt.subplots()
    self.ax.set_xlabel("Focus")
    self.ax.set_ylabel("Mean\nFWHM", rotation=0)
    self.ax.errorbar(self.foci, self.means, yerr=self.devs,
                     c='g', lw=1, marker='o', mfc='lime', mec='g',
                     capsize=5, ecolor='k')



# initialize
focName = "ASCOM.FocusLynx.Focuser" if Y24 else "ASCOM.OptecTCF_S.Focuser"
autofoc = AutoFocuser(focName, focGuess)
utc = time.strftime("UTC %Y-%m-%d %H:%M:%S", time.gmtime())

# parse command line arguments
parser = argparse.ArgumentParser(description="V curve")
parser.add_argument("-r", "--raw", action="store_true",
                    help="print raw data as it is collected")
parser.add_argument("-p", "--plot", action="store_true",
                    help="plot the curve using matplotlib")
parser.add_argument("-i", "--image", nargs="?", const=utc, default="",
                    metavar="FILE", help="export the plot to a file")
args = parser.parse_args()

# take a series of exposures and print data
autofoc.setupField()
autofoc.sampleRange(1500, 500)
autofoc.sampleRange(300, 200) # equivalent to (500, 200) because of culling
autofoc.sampleRange(100, 100) # culled to between 0 and 2 exposures
autofoc.report()

# plot a V-curve, if requested
if args.plot or args.image:
  autofoc.drawPlot()
  if args.image:
    autofoc.fig.savefig(args.image)
  if args.plot:
    autofoc.fig.show()
