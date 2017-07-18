
Y24 = True # set to False if script is being run on Y40
livePrint = False # print raw data as it's collected

expTime = 0.5
expCount = 4

focusGuess = 6000 # tests range in [4500, 7500]

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

    self.optimalFocus = focusGuess
    #self.rawdata = []
    self.foci = []
    self.means = []
    self.devs = []
    self.zeroes  = []

  # take a series of exposures over the range of focuser values in
  # [optimal - reach, optimal + reach] with a point every 'slice' units,
  # then store and analyze the data
  def sampleRange(self, reach, slice):
    self.focRange = range(self.optimalFocus - reach,
                          self.optimalFocus + reach + 1, slice)
    self.focRange = [f for f in self.focRange if not f in self.foci]
    self.foci.extend(self.focRange) # append non-duplicate focus values

    for f in self.focRange:
      self.focuser.Move(f)
      tmpData = ExposureData(f)
      if livePrint: print "\nFocus: %d" % f
      while self.focuser.IsMoving: continue

      for i in range(expCount):
        while self.cam.CameraStatus != 2: continue # "connected but inactive"
        self.cam.Expose(expTime, 1)
        time.sleep(0.1) # may not be long enough to prevent duplicates
        while self.cam.CameraStatus != 2: continue
        tmpData.fwhm.append(self.cam.FWHM if self.cam.FWHM else -1)
        if livePrint: print "FWHM: %.3f" % self.cam.FWHM

      tmpData.process()
      #self.rawdata.append(tmpData)
      self.foci.append(f)
      self.means.append(tmpData.mean)
      self.devs.append(tmpData.stdev)
      self.zeroes.append(tmpData.zerocount)
      self.minfwhm = np.min(self.fwhm)
      self.optimalFocus = self.foci[self.fwhm.index(self.minfwhm)]

  # print recorded data
  def report(self):
    print utc
    print "%f degC" % self.cam.AmbientTemperature
    print ("Focus,Mean FWHM(px), FWHM StdDev (px),",
           "Exposure (s),# Exposures,# Bad Exposures")
    for i in range(len(self.foci)):
      print "%d,%.3f,%.3f,%f,%d,%d" % (self.foci[i], self.means[i],
                                       self.devs[i], expTime, expCount,
                                       self.zeroes[i])
    print "Minimum FWHM is %.3f at a focus of %d" % (self.minfwhm,
                                                     self.optimalFocus)

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
autofoc = AutoFocuser(focName, 6000)
utc = time.strftime("UTC %Y-%m-%d %H:%M:%S", time.gmtime())

# parse command line arguments
parser = argparse.ArgumentParser(description="V curve")
parser.add_argument("-p", "--plot", action="store_true",
                    help="plot the curve using matplotlib")
parser.add_argument("-i", "--image", nargs="?", const=utc, default="",
                    metavar="FILE", help="export the plot to a file")
args = parser.parse_args()

# take a series of exposures and print data
autofoc.sampleRange(1500, 500)
autofoc.sampleRange(400, 200) # equivalent to (500, 200) because of culling
autofoc.sampleRange(100, 100) # will take between 0 and 2 exposures
autofoc.report()
sys.stdout.flush()

# plot a V-curve, if requested
if args.plot or args.image:
  autofoc.drawPlot()
  if args.image:
    autofoc.fig.savefig(args.image)
  if args.plot:
    autofoc.fig.show()
