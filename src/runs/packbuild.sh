#/usr/bin/bash

# build
export DAVAI_START_BUILD=`python -c "import time; print(time.time())"`
./runjob.py -n packbuild -t build.gmkpack.G2P_CL

# wait & check for build
export MTOOLDIR=/scratch/mtool/$LOGNAME  # needed to find cached expertise output of build
python vortex/bin/mkjob.py -j profile=rd name=wait4build task=build.wait4build
ok=$?

# return status of build
if [ "$ok" == "0" ];then
  echo "Build OK: continue"
  exit 0
else
  echo "Build KO ! $ok"
  exit 1
fi
