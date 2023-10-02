import copy
import logging
import time

import numpy as np
import torch
import boto3
import sagemaker
import os

from flamby.datasets.fed_heart_disease import (
    BATCH_SIZE,
    LR,
    NUM_EPOCHS_POOLED,
    Baseline,
    BaselineLoss,
    FedHeartDisease,
    metric,
)
from flamby.utils import evaluate_model_on_tests
from torch.optim import lr_scheduler

from fedml.core.alg_frame.client_trainer import ClientTrainer

# Arnab edits to incorporate sagemaker experiments
from sagemaker.session import Session
from sagemaker.experiments.run import Run, load_run
from sagemaker.utils import unique_name_from_base

class HeartDiseaseTrainer(ClientTrainer):
    def __init__(self, model, args=None):
        super().__init__(model, args)

    def get_model_params(self):
        return self.model.cpu().state_dict()

    def set_model_params(self, model_parameters):
        logging.info("set_model_params")
        self.model.load_state_dict(model_parameters)

    def train(self, train_data, device, args):
        logging.info("Start training on Trainer {}".format(self.id))
        model = self.model
        args = self.args
        
        # Define the IAM role ARN
        #role_arn = 'arn:aws:iam::871856899070:role/service-role/AmazonSageMaker-ExecutionRole-20210525T175740'

        # Create a new STS (Security Token Service) client
        #sts_client = boto3.client('sts')

        # Assume the IAM role to get temporary credentials
        #response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName='SageMakerSession')

        # Extract the temporary credentials
        #credentials = response['Credentials']
        #print(credentials)
        # Create a new SageMaker session with the temporary credentials
        #sagemaker_session = sagemaker.Session(
        #    aws_access_key_id=credentials['AccessKeyId'],
        #    aws_secret_access_key=credentials['SecretAccessKey'],
        #    aws_session_token=credentials['SessionToken']
        #)
        # Set the desired AWS region from env-vars, default to us-west-2
        region = os.getenv('AWS_REGION','us-west-2')  

        # Create a new Boto3 session with the specified region
        session = boto3.Session(region_name=region)
        # Create a Boto3 session using the default credentials
        #session = boto3.Session()

        # Create a SageMaker session using the SageMaker execution role
        sagemaker_session = sagemaker.Session(boto_session=session)
        
        epochs = args.epochs  # number of epochs

        from flamby.datasets.fed_heart_disease import BaselineLoss

        loss_func = BaselineLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=LR)

        since = time.time()

        best_model_wts = copy.deepcopy(model.state_dict())
        model = model.to(device)
        # To draw loss and accuracy plots
        training_loss_list = []
        training_auc_list = []

        logging.info(" Train Data Size " + str(len(train_data.dataset)))
        # logging.info(" Test Data Size " + str(dataset_sizes["test"]))
        #print(f"Arnab Arg Client Rank: {args.rank}")
        experiment_name = unique_name_from_base(args.sm_experiment_name + "-client-" + str(args.rank))
        print(f"Sagemaker Experiment Name: {experiment_name}")
        
        for epoch in range(epochs):
            logging.info("Epoch {}/{}".format(epoch, epochs - 1))
            logging.info("-" * 10)

            running_loss = 0.0
            auc = 0.0
            model.train()  # Set model to training mode

            # Iterate over data.
            for idx, (X, y) in enumerate(train_data):
                X = X.to(device)
                y = y.to(device)

                optimizer.zero_grad()
                y_pred = model(X)
                loss = loss_func(y_pred, y)
                loss.backward()
                optimizer.step()
                running_loss += loss.item()
                auc += metric(y_pred.detach().cpu().numpy(), y.detach().cpu().numpy())

            epoch_loss = running_loss / len(train_data.dataset)
            epoch_auc = auc / len(train_data.dataset)

            logging.info(
                "Training Loss: {:.4f} Validation AUC: {:.4f} ".format(
                    epoch_loss, epoch_auc
                )
            )
            training_loss_list.append(epoch_loss)
            training_auc_list.append(epoch_auc)
            # Steps to push  training metrics to Sagemaker Experiments
            run_name = "trial-run-" + str(epoch)
            print(run_name)
            
            # create an experiment and start a new run
            with Run(experiment_name=experiment_name, run_name=run_name, sagemaker_session=sagemaker_session ) as run:
                run.log_parameters(
                    { "Train Data Size": str(len(train_data.dataset)),
                      "device": "cpu",
                      "center": args.rank,
                      "learning-rate": args.lr,
                      "batch-size": args.batch_size,
                      "client-optimizer" : args.client_optimizer,
                      "weight-decay": args.weight_decay
                    }
                )
                run.log_metric(name="Validation:AUC", value=epoch_auc)
                run.log_metric(name="Training:Loss", value=epoch_loss)                        

        time_elapsed = time.time() - since
        logging.info(
            "Training complete in {:.0f}m {:.0f}s".format(
                time_elapsed // 60, time_elapsed % 60
            )
        )
        logging.info("----- Training Loss ---------")
        logging.info(training_loss_list)
        logging.info("------Validation AUC ------")
        logging.info(training_auc_list)
        return model
