#!/bin/bash
#SBATCH --chdir=/home/700050058/UAEU-4khumandataset
#SBATCH --job-name=filter_data
#SBATCH --output=log/filter_data_%A_%a.out
#SBATCH --error=log/filter_data_%A_%a.err
#SBATCH --array=0-7
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=20G
#SBATCH --partition=longq
#SBATCH --time=30:00:00
#SBATCH --mail-user=700050058@uaeu.ac.ae
#SBATCH --mail-type=END,FAIL

module load anaconda3
source $(conda info --base)/etc/profile.d/conda.sh
conda activate preprocess_videos

# 防止 numpy / mkl 抢线程
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

python filter_qualified.py
