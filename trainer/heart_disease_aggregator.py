import logging

import numpy as np
import torch
import torch.nn as nn

import fedml
from fedml.core import ServerAggregator
# Arnab edits to incorporate sagemaker experiments
import boto3
import sagemaker
import os
from sagemaker.session import Session
from sagemaker.experiments.run import Run, load_run
from sagemaker.utils import unique_name_from_base


class HeartDiseaseAggregator(ServerAggregator):
    def get_model_params(self):
        return self.model.cpu().state_dict()

    def set_model_params(self, model_parameters):
        logging.info("set_model_params")
        self.model.load_state_dict(model_parameters)

    def test(self, test_data, device, args):
        pass

    def _test(self, test_data, device):
        logging.info("Evaluating on Trainer ID: {}".format(self.id))
        model = self.model
        args = self.args

        test_metrics = {
            "test_correct": 0,
            "test_total": 0,
            "test_loss": 0,
        }

        if not test_data:
            logging.info("No test data for this trainer")
            return test_metrics

        model.eval()
        model.to(device)

        from flamby.datasets.fed_heart_disease.metric import metric

        with torch.inference_mode():
            auc_list = []
            for (X, y) in test_data:
                X, y = X.to(device), y.to(device)
                y_pred = model(X)
                auc = metric(y_pred.detach().cpu().numpy(), y.detach().cpu().numpy())
                auc_list.append(auc)

            test_metrics = np.mean(auc_list)

        logging.info(f"Test metrics: {test_metrics}")
        return test_metrics

    def test_all(
        self, train_data_local_dict, test_data_local_dict, device, args=None
    ) -> bool:
        model = self.model
        args = self.args
        from flamby.datasets.fed_heart_disease.metric import metric
        from flamby.datasets.fed_heart_disease import BaselineLoss
       
        # Set the desired AWS region from environment variable, defaults to us-west-2
        region = os.getenv('AWS_REGION','us-west-2')

        # Create a new Boto3 session with the specified region
        session = boto3.Session(region_name=region)
        # Create a Boto3 session using the default credentials
        #session = boto3.Session()

        # Create a SageMaker session using the SageMaker execution role
        sagemaker_session = sagemaker.Session(boto_session=session)

        
        test_metrics = {
            "test_correct": 0,
            "test_total": 0,
            "test_loss": 0,
        }
        
        if not test_data_local_dict:
            logging.info("No test data for this trainer")
            return test_metrics

        model.eval()
        model.to(device)
        
        experiment_name = unique_name_from_base(args.sm_experiment_name + "-server-")
        print(f"Sagemaker Experiment Name: {experiment_name}")

        to_avg_auc_list, to_avg_loss_list = [], []
        w = []
        debug_list = []
        for i in range(args.client_num_per_round):
            loss_func = BaselineLoss()
            # Steps to push  training metrics to Sagemaker Experiments
            run_name = "client-round-run-" + str(i)
            print(run_name)
            
            with torch.inference_mode():
                auc_list = []
                loss_list = []
                w.append(len(test_data_local_dict[i]))
                for (X, y) in test_data_local_dict[i]:
                    X, y = X.to(device), y.to(device)
                    y_pred = model(X)

                    if len(debug_list) == 0:
                        debug_list.append(y_pred.detach().cpu().numpy())

                    auc = metric(y.detach().cpu().numpy(), y_pred.detach().cpu().numpy())
                    loss = loss_func(y_pred, y)

                    auc_list.append(auc)
                    loss_list.append(loss.item())
                
                test_auc_metrics = np.mean(auc_list)
                test_loss_metrics = np.mean(loss_list)
            to_avg_auc_list.append(test_auc_metrics)
            to_avg_loss_list.append(test_loss_metrics)
            
            # create an experiment and start a new run
            with Run(experiment_name=experiment_name, run_name=run_name, sagemaker_session=sagemaker_session ) as run:
                run.log_parameters(
                    { "Test Data Size": str(len(test_data_local_dict[i])),
                      "device": "cpu",
                      "round": i,
                      "learning-rate": args.lr,
                      "batch-size": args.batch_size,
                      "client-optimizer" : args.client_optimizer,
                      "weight-decay": args.weight_decay
                    }
                )
                run.log_metric(name="Test:AUC", value=test_auc_metrics)
                run.log_metric(name="Test:Loss", value=test_loss_metrics) 
        # avg
        avg_auc = np.average(to_avg_auc_list, weights=w)
        avg_loss = np.average(to_avg_loss_list, weights=w)
        print("Average AUC performance", avg_auc)
        print("Average Loss performance", avg_loss)

        print ({"round_idx": args.round_idx, "loss": avg_loss, "evaluation_result": avg_auc})
        fedml.mlops.log({"round_idx": args.round_idx, "loss": avg_loss, "evaluation_result": avg_auc})
        test_metrics["test_correct"] = avg_auc
        test_metrics["test_total"] = avg_auc
        test_metrics["test_loss"] = avg_loss
        return test_metrics
