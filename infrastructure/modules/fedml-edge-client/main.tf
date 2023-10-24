provider "aws" {
  region = local.region
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  token                  = data.aws_eks_cluster_auth.this.token
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    token                  = data.aws_eks_cluster_auth.this.token
  }
}

provider "bcrypt" {}

data "aws_eks_cluster_auth" "this" {
  name = module.eks.cluster_name
}

data "aws_availability_zones" "available" {}

locals {
  name   = var.name
  region = "us-west-2"

  cluster_version = "1.25"

  vpc_cidr = "10.0.0.0/16"
  azs      = slice(data.aws_availability_zones.available.names, 0, 3)

  namespace = "fedml"
  fedml_sa = "fedml-sa"


  tags = {
    Blueprint  = var.name
    GithubRepo = "github.com/aws-ia/terraform-aws-eks-blueprints"
  }
}

################################################################################
# Cluster
################################################################################

#tfsec:ignore:aws-eks-enable-control-plane-logging

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.17.2"

  cluster_name                   = var.name
  cluster_version                = local.cluster_version
  cluster_endpoint_public_access = true

  # EKS Addons
  cluster_addons = {
    coredns    = {}
    kube-proxy = {}
    vpc-cni    = {}
  }

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {

    node_group_a = {
      
      min_size     = 1
      max_size     = 5
      desired_size = 2
      
      instance_types = ["c5.2xlarge"]
      use_custom_launch_template = false
      disk_size      = 100
  }

  }

  tags = local.tags
}

/*
################################################################################
# Kubernetes Addons
################################################################################

module "eks_blueprints_kubernetes_addons" {
  source = "github.com/aws-ia/terraform-aws-eks-blueprints//modules/kubernetes-addons?ref=v4.32.1"

  eks_cluster_id       = module.eks.cluster_name
  eks_cluster_endpoint = module.eks.cluster_endpoint
  eks_oidc_provider    = module.eks.oidc_provider
  eks_cluster_version  = module.eks.cluster_version

  enable_argocd = true
  # This example shows how to set default ArgoCD Admin Password using SecretsManager with Helm Chart set_sensitive values.
  argocd_helm_config = {
    set_sensitive = [
      {
        name  = "configs.secret.argocdServerAdminPassword"
        value = bcrypt_hash.argo.id
      }
    ]
  }

  keda_helm_config = {
    values = [
      {
        name  = "serviceAccount.create"
        value = "false"
      }
    ]
  }

  argocd_manage_add_ons = true # Indicates that ArgoCD is responsible for managing/deploying add-ons
  argocd_applications = {
    addons = {
      path               = "chart"
      repo_url           = "https://github.com/aws-samples/eks-blueprints-add-ons.git"
      add_on_application = true
    }
    workloads = {
      path               = "devops/k8s/fedml-edge-client-server/fedml-client-deployment"
      repo_url           = "https://github.com/awshans/FedML.git"
      add_on_application = true
      values = {
        env = {
          fedmlAccountId   = "2335"
        }
        serviceAccount = {
          annotations = {
            "eks.amazonaws.com/role-arn" = module.fedml_role.iam_role_arn
          }
        }
      }
    }
  }

  # Add-ons
  enable_amazon_eks_aws_ebs_csi_driver = true
  enable_aws_for_fluentbit             = true
  
  # Let fluentbit create the cw log group
  aws_for_fluentbit_create_cw_log_group = false
  enable_cert_manager                   = true
  enable_cluster_autoscaler             = false
  enable_karpenter                      = false
  enable_keda                           = false
  enable_metrics_server                 = true
  enable_prometheus                     = false
  enable_traefik                        = false
  enable_vpa                            = false
  enable_yunikorn                       = false
  enable_argo_rollouts                  = false

  tags = local.tags
}
*/

#---------------------------------------------------------------
# ArgoCD Admin Password credentials with Secrets Manager
# Login to AWS Secrets manager with the same role as Terraform to extract the ArgoCD admin password with the secret name as "argocd"
#---------------------------------------------------------------
resource "random_password" "argocd" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Argo requires the password to be bcrypt, we use custom provider of bcrypt,
# as the default bcrypt function generates diff for each terraform plan
resource "bcrypt_hash" "argo" {
  cleartext = random_password.argocd.result
}

#tfsec:ignore:aws-ssm-secret-use-customer-key
resource "aws_secretsmanager_secret" "argocd" {
  name                    = "argocd_${var.name}"
  recovery_window_in_days = 0 # Set to zero for this example to force delete during Terraform destroy
  kms_key_id = aws_kms_key.managed_kms_key.id
}

resource "aws_secretsmanager_secret_version" "argocd" {
  secret_id     = aws_secretsmanager_secret.argocd.id
  secret_string = random_password.argocd.result
}

resource "aws_kms_key" "managed_kms_key" {
  description             = "KMS key used for ${var.name} Argo admin sercret"
  deletion_window_in_days = 10
  enable_key_rotation = true
}

################################################################################
# IRSA
################################################################################

module "fedml_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.20"

  role_name_prefix = "${module.eks.cluster_name}-fedml-"

  role_policy_arns = {
    policy = aws_iam_policy.fedml.arn
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["fedml:fedml-sa"]
    }
  }

  tags = local.tags
}

resource "aws_iam_policy" "fedml" {
  name_prefix = local.fedml_sa
  policy      = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:UpdateTrial",
        "sagemaker:CreateTrial",
        "sagemaker:UpdateExperiment",
        "sagemaker:CreateExperiment",
        "sagemaker:UpdateTrialComponent",
        "sagemaker:CreateTrialComponent",
        "sagemaker:AddTags",
        "sagemaker:AssociateTrialComponent",
        "sagemaker:BatchPutMetrics",
        "sagemaker:DescribeExperiment",
        "sagemaker:DescribeTrial"
      ],
      "Resource": "arn:aws:sagemaker:us-west-2:*:experiment/*"
    }
  ]
}
POLICY
}

################################################################################
# Supporting Resources
################################################################################

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 4.0"

  name = var.name
  cidr = local.vpc_cidr

  azs             = local.azs
  private_subnets = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 4, k)]
  public_subnets  = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k + 48)]

  enable_nat_gateway = true
  single_nat_gateway = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }

  tags = local.tags
}
