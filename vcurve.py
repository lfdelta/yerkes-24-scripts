
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
##                    Yerkes Observatory 24" Refractor                    ##
############################################################################

# setup
from win32com.client import Dispatch
import numpy as np, matplotlib.pyplot as plt
import sys, argparse, time

def quit(msg):
  print msg
  sys.exit()

utc = time.strftime("UTC %Y-%m-%d %H:%M:%S", time.gmtime())
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

focus = Dispatch("ASCOM.FocusLynx.Focuser")
focus.Connected = True
focus.Link = True
if not (focus.Connected and focus.Link): quit("Focuser failed to connect")
if not focus.Absolute: quit("Focuser does not support absolute positioning")

# take multiple exposures over the given focus range, and export data
print utc
print "Focus,Mean FWHM (px),FWHM StdDev (px),Exposure (s),# Exposures"
foci = range(focusMin, focusMax + 1, focusStep)
fwhm = []
devs = []
for f in foci:
  focus.Move(f)
  while focus.IsMoving: continue

  # expose photo and collect FWHM
  samples=[]
  for i in range(expCount):
    while cam.CameraStatus == 3: continue # 3 -> "is exposing a light image"
    cam.Expose(expTime, 1)
    samples.append(cam.FWHM)

  # compile and store FWHM data
  mean = np.average(samples)
  stdev = np.std(samples)
  fwhm.append(mean)
  devs.append(stdev)
  print "%d,%.3f,%.3f,%f,%d" % (f, mean, stdev, expTime, expCount)

minf = np.min(fwhm)
print "Minimum FWHM is %6.3f at a focus of %d" % (minf, foci[fwhm.index(minf)])
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
