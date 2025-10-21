# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import sys
import os

sys.path.insert(0, os.path.abspath('./tt'))

from DataStorage import TTDataStorage, TTDataUnit
from Compute import TTCompute
from Ensemble import TTEnsemble
from Radio import TTWIFI, WLANProtocol

sd_storage = TTDataStorage("sd_card", 64, TTDataUnit.GB, {"vendor":"samsung"})
emmc_storage = TTDataStorage("emmc_onboard", 32, TTDataUnit.GB)
main_memory = TTDataStorage("ram", 8, TTDataUnit.GB)

denver_compute = TTCompute("denver", 2, main_memory)
arm_compute = TTCompute("arm", 4, main_memory)
cuda_compute = TTCompute("cuda", 256, main_memory)

wifi = TTWIFI("wifi", "FF:FF:FF:FF:FF:FF", WLANProtocol.B)

jetson = TTEnsemble("jetson")
jetson.addComponents(sd_storage, emmc_storage, main_memory, denver_compute, arm_compute, cuda_compute, wifi)
jetson.pickleToFile("./pickle")