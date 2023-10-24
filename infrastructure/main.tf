
module "m_fedml_edge_client_1" {
    source            = "./modules/fedml-edge-client"
    name              = "fedml-edge-client-1"
    # region            = local.region
    # vpc_cidr          = local.vpc_cidr
    # azs               = local.azs
    # tags              = local.tags
}

module "m_fedml_edge_client_2" {
    source            = "./modules/fedml-edge-client"
    name              = "fedml-edge-client-2"
    # region            = local.region
    # vpc_cidr          = local.vpc_cidr
    # azs               = local.azs
    # tags              = local.tags
}

module "m_fedml_edge_server" {
    source            = "./modules/fedml-edge-server"
    name              = "fedml-edge-server"
    # region            = local.region
    # vpc_cidr          = local.vpc_cidr
    # azs               = local.azs
    # tags              = local.tags
}
