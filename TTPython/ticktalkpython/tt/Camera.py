# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from Sensor import TTSensor;
from Component import TTComponent
from Query import TTQComponent

class TTCamera(TTSensor):

    def __init__(self, image_width, image_height, FOV=[0,0], fps=0, flip = 0, angle = 0, height = 0):
        super().__init__()
        self.image_width = image_width
        self.image_height = image_height
        self.FOV = FOV
        self.fps = fps
        self.flip = flip
        self.angle = angle
        self.focalLength = self.image_height / 2 / math.tan(self.FOV[1] / 2.0)

class TTQCamera(TTQSensor):
    def __init__(self, image_width, image_height, FOVx, FOVy, fps, flip, angle, height):
        super().__init__(image_width, image_height, FOVx, FOVy, fps, flip, angle, height)
    def test(self, component):
        if(not isinstance(component, TTQCamera)):
            return False
        else:
            # if self
            pass

def camera():
    pass