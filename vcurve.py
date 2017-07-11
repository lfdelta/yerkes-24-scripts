
Y24 = True # set to False if script is being run on Y40

expTime = 10.0
expCount = 5

focusMin = 5000
focusMax = 7000
focusStep = 125

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

# setup
from win32com.client import Dispatch
import numpy as np, matplotlib.pyplot as plt
import sys, argparse, time

def quit(msg):
  print msg
  sys.exit()

utc = time.strftime("UTC %Y-%m-%d %H:%M:%S", time.gmtime())

# parse command line arguments
parser = argparse.ArgumentParser(description="V curve")
parser.add_argument("-p", "--plot", action="store_true",
                    help="plot the curve using matplotlib")
parser.add_argument("-i", "--image", nargs="?", const=utc, default="",
                    metavar="FILE", help="export the plot to a file")
args = parser.parse_args()

# establish connections to CCD (via MaximDL) and focuser
cam = Dispatch("MaxIm.CCDCamera")
cam.LinkEnabled = True
if not cam.LinkEnabled: quit("Camera failed to connect")

focus = Dispatch("ASCOM.FocusLynx.Focuser" if Y24
                 else "ASCOM.OptecTCF_S.Focuser")
focus.Connected = True
focus.Link = True
if not (focus.Connected and focus.Link): quit("Focuser failed to connect")
if not focus.Absolute: quit("Focuser does not support absolute positioning")

# take multiple exposures over the given focus range, and export data
print utc
print "%f %sC" % (cam.AmbientTemperature, unichr(0x00B0))
print "Focus,Mean FWHM (px),FWHM StdDev (px),Exposure (s),# Exposures,# Bad Exposures"
foci = range(focusMin, focusMax + 1, focusStep)
fwhm = []
devs = []
for f in foci:
  zeroes = 0 # number of zero-measure FWHM in this sample
  focus.Move(f)
  while focus.IsMoving: continue

  # expose photo and collect FWHM
  samples=[]
  for i in range(expCount):
    while cam.CameraStatus != 2: continue # 2 -> "connected but inactive"
    cam.Expose(expTime, 1)
    time.sleep(0.1) # this may not be sufficiently long to prevent duplicates
    while cam.CameraStatus != 2: continue
    samples.append(cam.FWHM if cam.FWHM > 0 else -1)
    if cam.FWHM == 0: zeroes += 1

  # compile and store FWHM data
  samples = [x for x in samples if x > 0] # don't analyze bad data
  if samples == []:
    mean = stdev = -1
  else:
    mean = np.average(samples)
    stdev = np.std(samples)
    fwhm.append(mean)
    devs.append(stdev)
  print "%d,%.3f,%.3f,%f,%d,%d" % (f, mean, stdev, expTime, expCount, zeroes)

minf = np.min(fwhm)
print "Minimum FWHM is %.3f at a focus of %d" % (minf, foci[fwhm.index(minf)])
sys.stdout.flush()

# plot a V curve based upon the data collected
if args.plot or args.image:
  fig, ax = plt.subplots()
  ax.set_xlabel("Focus")
  ax.set_ylabel("Mean\nFWHM", rotation=0)
  ax.errorbar(foci, fwhm, yerr=devs,
              c='g', lw=1, marker='o', mfc='lime', mec='g',
              capsize=5, ecolor='k')
  if args.image:
    fig.savefig(args.image)
  if args.plot:
    plt.show()
