# Federated Learning on AWS using FedML.ai

This project used fedml.ai APIs to do cross-silo(Octopus) training on AWS.
Amazon Sagemaker is used for experiment tracking.
The project is using FLamby, which is a benchmark for cross-silo federated
learning.

This code will work on any x86 based compute platform.
The project has been tested on the following compute services: EC2 & EKS


## Heart Disease

The Heart Disease dataset [1] was collected in 1988 in four centers:
Cleveland, Hungary, Switzerland and Long Beach V. We do not own the
copyright of the data: everyone using this dataset should abide by its
licence and give proper attribution to the original authors. It is
available for download
[here](https://archive-beta.ics.uci.edu/ml/datasets/heart+disease).

## Dataset description

|                    | Dataset description                                           |
| ------------------ | ------------------------------------------------------------- |
| Description        | Heart Disease dataset.                                        |
| Dataset size       | 39,6 KB.                                                      |
| Centers            | 4 centers - Cleveland, Hungary, Switzerland and Long Beach V. |
| Records per center | Train/Test: 199/104, 172/89, 30/16, 85/45.                    |
| Inputs shape       | 16 features (tabular data).                                   |
| Total nb of points | 740.                                                          |
| Task               | Binary classification                                         |

## Data Download instructions

Set download in the config file to True. Note that please only set download to True at the first time you run the code.

```yaml
data_args:
  dataset: "Fed-Heart-Disease"
  data_cache_dir: ~/healthcare/heart_disease # flamby
  partition_method: "hetero"
  partition_alpha: 0.5
  debug: false # flamby: debug or not
  preprocessed: false # flamby: preprocessed or not, need to preprocess in first
  download: true # flamby: download or not
```

**IMPORTANT :** If you choose to relocate the dataset after downloading it, it is
imperative that you run the following script otherwise all subsequent scripts will not find it:

```
python update_config.py --new-path /new/path/towards/dataset
```

## Start Training using Fedml.ai MLOps UI

### Register for a Fedml MLOps account
- You need to sign up for a MLOps account id here: [SignUp](https://open.fedml.ai/login)

### Execute Terraform to deploy EKS clusters
- Pass your account id as an input to your terraform setup

### Confirm Edge Devices in UI
- Check in the UI you see your FedML Clients and Aggregation server here: [Edge Devices](https://open.fedml.ai/octopus/edgeDevice/edgeApp)

### Create an Application
- Use the FedML.ai [new Application UI](https://open.fedml.ai/octopus/applications/index) to create an app. In this case you will be creating a heart disease app.
- Next upload the client and server jars

### Initiate Federated Training
- Create a project [New Project](https://open.fedml.ai/octopus/project/index)
- Add your edge Devices
- Choose the applications
- Hit "Start Run"
You should then see the "Training Tab" and the status of the training run.

# Contributors
- Randy DeFauw
- Tamer Sherif
- Prachi Kulkarni
- Hans Nesbitt
- Arnab Sinha 


# Citation:

```bash
@article{he2021fedcv,
  title={Fedcv: a federated learning framework for diverse computer vision tasks},
  author={He, Chaoyang and Shah, Alay Dilipbhai and Tang, Zhenheng and Sivashunmugam, Di Fan1Adarshan Naiynar and Bhogaraju, Keerti and Shimpi, Mita and Shen, Li and Chu, Xiaowen and Soltanolkotabi, Mahdi and Avestimehr, Salman},
  journal={arXiv preprint arXiv:2111.11066},
  year={2021}
}
@misc{he2020fedml,
      title={FedML: A Research Library and Benchmark for Federated Machine Learning},
      author={Chaoyang He and Songze Li and Jinhyun So and Xiao Zeng and Mi Zhang and Hongyi Wang and Xiaoyang Wang and Praneeth Vepakomma and Abhishek Singh and Hang Qiu and Xinghua Zhu and Jianzong Wang and Li Shen and Peilin Zhao and Yan Kang and Yang Liu and Ramesh Raskar and Qiang Yang and Murali Annavaram and Salman Avestimehr},
      year={2020},
      eprint={2007.13518},
      archivePrefix={arXiv},
      primaryClass={cs.LG}
}
```
