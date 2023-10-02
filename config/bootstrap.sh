### don't modify this part ###
set -x
##############################


### please customize your script in this region ####
pip install batchgenerators
pip install boto3 sagemaker
git clone https://github.com/owkin/FLamby.git
cd FLamby
git checkout 4e16a40e8d710c60969added2f022b89dccc1174
pip install -e .
#python3 setup.py install

DATA_PATH=$HOME/healthcare/heart_disease
mkdir -p $DATA_PATH


### don't modify this part ###
exit 0
##############################