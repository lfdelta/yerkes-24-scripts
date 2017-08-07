
def subframe(width, height, CameraXSize, CameraYSize, MaxPixelX, MaxPixelY):
  width = min(width, CameraXSize)
  height = min(height, CameraYSize)
  naiveX = MaxPixelX - (width/2) # upper-left corner of subframe
  naiveY = MaxPixelY - (height/2)
  lbX = max(0, naiveX) # set lower bound = 0
  lbY = max(0, naiveY)
  ubX = min(lbX, CameraXSize - width) # set upper bound
  ubY = min(lbY, CameraYSize - height)
  StartX = ubX
  StartY = ubY
  NumX = width
  NumY = height

  img = []
  for j in range(CameraYSize):
    img.append(["."] * CameraXSize)

  for y in range(StartY, StartY + NumY):
    for x in range(StartX, StartX + NumX):
      img[y][x] = "@"

  img[MaxPixelY][MaxPixelX] = "*"

  for i in range(len(img)):
    img[i] = "".join(img[i])

  for row in img:
    print row
