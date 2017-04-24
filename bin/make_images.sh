#!/bin/bash -l
#SBATCH --account=mwasci
#SBATCH --partition=gpuq
#SBATCH --time=20:00:00
#SBATCH --nodes=1
#SBATCH --mem=32gb
#SBATCH --output=/scratch2/mwasci/phancock/D0009/queue/make_image.o%A
#SBATCH --error=/scratch2/mwasci/phancock/D0009/queue/make_image.e%A

aprun='aprun -n 1 -d 8 -b'

datadir=/scratch2/mwasci/phancock/D0009/processing

cd $datadir

obsnum=OBSNUM
ncpus=8

# make the high time resolution images but don't clean
$aprun wsclean -name ${obsnum}/${obsnum}-hr -size 320 320 \
               -weight briggs 0.5 -mfsweighting -scale 25.0amin \
               -pol I -niter 0 \
               -interval 0 232 -intervalsout 232 \
               -maxuv-l 32 -minuv-l 0.03 -smallinversion -j ${ncpus} \
               ${obsnum}/${obsnum}.ms
               #-joinchannels -stopnegative -joinpolarizations -niter 4000 -threshold 1.0 \ # don't clean

# make the 2min image and clean
$aprun wsclean -name ${obsnum}/${obsnum}-lr \
               -weight briggs 0.5 -mfsweighting -scale 25.0amin \
               -pol I -j ${ncpus} \
               -joinchannels -stopnegative -joinpolarizations -niter 4000 -threshold 1.0 \
               ${obsnum}/${obsnum}.ms
